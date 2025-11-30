"""
MV Production Automation Agent (Lupinus, Iris, Fiona)
StreamlitベースのMV制作自動化パイプラインアプリケーション
"""

import os
import sys
import streamlit as st
from pathlib import Path
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import json

# ローカルモジュールのインポート
from media_processor import MediaProcessor
from prompt_generator import PromptGenerator
from character_manager import CharacterManager
from prompt_dialogs import SunoPromptDialog, ImagePromptDialog, VideoPromptDialog, CharacterImageDialog
from prompt_history import PromptHistory
from PIL import Image

# プロジェクトのベースパス
BASE_DIR = Path(r"C:\MVAI")

# API Key保存ファイルのパス
API_KEY_FILE = BASE_DIR / ".api_key.json"

# 必要なフォルダの定義
REQUIRED_FOLDERS = [
    "00_キャラクター",
    "01_曲_Input",
    "02_元動画_Sora",
    "03_静止画_選定",
    "04_AI動画_生成中",
    "05_動画_高品質化",
    "06_動画_口パク",
    "98_MV_完成品",
    "99_MV_編集素材",
    "99_Logs"
]

# セッション状態の初期化
if 'api_key_set' not in st.session_state:
    st.session_state.api_key_set = False
if 'observer' not in st.session_state:
    st.session_state.observer = None
if 'processing_logs' not in st.session_state:
    st.session_state.processing_logs = []
if 'watchdog_running' not in st.session_state:
    st.session_state.watchdog_running = False
if 'show_api_input' not in st.session_state:
    st.session_state.show_api_input = False


def create_folders():
    """必要なフォルダを自動作成"""
    created_folders = []
    for folder in REQUIRED_FOLDERS:
        folder_path = BASE_DIR / folder
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            created_folders.append(folder)
    return created_folders


def load_api_key():
    """保存されたAPI Keyを読み込む"""
    if API_KEY_FILE.exists():
        try:
            with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('api_key', '')
        except Exception:
            return ''
    return ''


def save_api_key(api_key: str):
    """API Keyをファイルに保存"""
    try:
        data = {'api_key': api_key}
        with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        # ファイルの権限を制限（可能な場合）
        if hasattr(os, 'chmod'):
            try:
                os.chmod(API_KEY_FILE, 0o600)
            except Exception:
                pass  # Windowsでは権限設定ができない場合がある
        return True
    except Exception as e:
        # エラーは呼び出し元で処理
        print(f"API Keyの保存に失敗しました: {str(e)}")
        return False


def setup_gemini_api(api_key: str):
    """Gemini APIの設定"""
    try:
        genai.configure(api_key=api_key)
        os.environ['GEMINI_API_KEY'] = api_key
        # API Keyを保存
        save_api_key(api_key)
        return True
    except Exception as e:
        st.error(f"API Keyの設定に失敗しました: {str(e)}")
        return False


def add_log(message: str, log_type: str = "INFO"):
    """処理ログを追加"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "type": log_type,
        "message": message
    }
    st.session_state.processing_logs.append(log_entry)
    # ログが多すぎる場合は古いものを削除（最新100件を保持）
    if len(st.session_state.processing_logs) > 100:
        st.session_state.processing_logs = st.session_state.processing_logs[-100:]


def start_watchdog():
    """Watchdog監視を開始"""
    if st.session_state.watchdog_running:
        return
    
    try:
        media_processor = MediaProcessor(BASE_DIR, add_log)
        event_handler = MediaFileHandler(media_processor)
        
        observer = Observer()
        
        # 監視対象フォルダを追加
        observer.schedule(event_handler, str(BASE_DIR / "01_曲_Input"), recursive=False)
        observer.schedule(event_handler, str(BASE_DIR / "02_元動画_Sora"), recursive=False)
        observer.schedule(event_handler, str(BASE_DIR / "04_AI動画_生成中"), recursive=False)
        observer.schedule(event_handler, str(BASE_DIR / "05_動画_高品質化"), recursive=False)
        observer.schedule(event_handler, str(BASE_DIR / "06_動画_口パク"), recursive=False)
        
        observer.start()
        st.session_state.observer = observer
        st.session_state.watchdog_running = True
        add_log("Watchdog監視を開始しました", "SUCCESS")
    except Exception as e:
        add_log(f"Watchdogの起動に失敗しました: {str(e)}", "ERROR")


def stop_watchdog():
    """Watchdog監視を停止"""
    if st.session_state.observer:
        try:
            st.session_state.observer.stop()
            st.session_state.observer.join()
            st.session_state.observer = None
            st.session_state.watchdog_running = False
            add_log("Watchdog監視を停止しました", "INFO")
        except Exception as e:
            add_log(f"Watchdogの停止に失敗しました: {str(e)}", "ERROR")


class MediaFileHandler(FileSystemEventHandler):
    """ファイルシステムイベントハンドラー"""
    
    def __init__(self, media_processor):
        super().__init__()
        self.media_processor = media_processor
        self.processed_files = set()
    
    def on_created(self, event):
        """ファイル作成時の処理"""
        try:
            if event.is_directory:
                return
            
            file_path = Path(event.src_path)
            
            # 重複処理を防ぐ
            if str(file_path) in self.processed_files:
                return
            
            # ファイルが完全に書き込まれるまで待機
            time.sleep(1)
            
            if not file_path.exists():
                return
            
            # ファイル拡張子のチェック（対応していないファイルはスキップ）
            valid_audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
            valid_video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            
            file_ext = file_path.suffix.lower()
            parent_folder = file_path.parent.name
            
            # 対応していないファイル形式はスキップ
            if parent_folder == "01_曲_Input" and file_ext not in valid_audio_extensions:
                self.media_processor.log_callback(
                    f"対応していない音声ファイル形式です: {file_path.name} ({file_ext})",
                    "ERROR"
                )
                return
            
            if parent_folder == "02_元動画_Sora" and file_ext not in valid_video_extensions:
                self.media_processor.log_callback(
                    f"対応していない動画ファイル形式です: {file_path.name} ({file_ext})",
                    "ERROR"
                )
                return
            
            self.processed_files.add(str(file_path))
            
            # フォルダに応じた処理を実行
            if parent_folder == "01_曲_Input":
                threading.Thread(
                    target=self._safe_process_audio,
                    args=(file_path,),
                    daemon=True
                ).start()
            elif parent_folder == "02_元動画_Sora":
                threading.Thread(
                    target=self._safe_process_video,
                    args=(file_path,),
                    daemon=True
                ).start()
            elif parent_folder == "04_AI動画_生成中":
                threading.Thread(
                    target=self._safe_trigger_quality,
                    args=(file_path,),
                    daemon=True
                ).start()
            elif parent_folder == "05_動画_高品質化":
                threading.Thread(
                    target=self._safe_process_lipsync,
                    args=(file_path,),
                    daemon=True
                ).start()
            elif parent_folder == "06_動画_口パク":
                threading.Thread(
                    target=self._safe_finalize_assets,
                    args=(file_path,),
                    daemon=True
                ).start()
        except Exception as e:
            # エラーをログに記録（log_callbackが利用可能な場合）
            try:
                if hasattr(self, 'media_processor') and self.media_processor:
                    self.media_processor.log_callback(
                        f"ファイル処理エラー: {str(e)}",
                        "ERROR"
                    )
            except:
                pass  # ログ記録も失敗した場合は無視
    
    def _safe_process_audio(self, file_path: Path):
        """音声処理の安全なラッパー"""
        try:
            self.media_processor.process_audio_file(file_path)
        except Exception as e:
            self.media_processor.log_callback(
                f"音声処理で予期しないエラーが発生しました ({file_path.name}): {str(e)}",
                "ERROR"
            )
    
    def _safe_process_video(self, file_path: Path):
        """動画処理の安全なラッパー"""
        try:
            self.media_processor.process_video_file(file_path)
        except Exception as e:
            self.media_processor.log_callback(
                f"動画処理で予期しないエラーが発生しました ({file_path.name}): {str(e)}",
                "ERROR"
            )
    
    def _safe_trigger_quality(self, file_path: Path):
        """高品質化トリガーの安全なラッパー"""
        try:
            self.media_processor.trigger_quality_pipeline(file_path)
        except Exception as e:
            self.media_processor.log_callback(
                f"高品質化パイプラインで予期しないエラーが発生しました ({file_path.name}): {str(e)}",
                "ERROR"
            )
    
    def _safe_process_lipsync(self, file_path: Path):
        """リップシンク処理の安全なラッパー"""
        try:
            self.media_processor.process_lipsync(file_path)
        except Exception as e:
            self.media_processor.log_callback(
                f"リップシンク処理で予期しないエラーが発生しました ({file_path.name}): {str(e)}",
                "ERROR"
            )
    
    def _safe_finalize_assets(self, file_path: Path):
        """最終処理の安全なラッパー"""
        try:
            self.media_processor.finalize_assets(file_path)
        except Exception as e:
            self.media_processor.log_callback(
                f"最終処理で予期しないエラーが発生しました ({file_path.name}): {str(e)}",
                "ERROR"
            )


# Streamlit UI
def main():
    st.set_page_config(
        page_title="MV Production Automation Agent",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 MV Production Automation Agent")
    st.markdown("### Lupinus, Iris, Fiona - MV制作自動化パイプライン")
    
    # サイドバー: API Key設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 保存されたAPI Keyを読み込む
        saved_key = load_api_key()
        existing_key = os.environ.get('GEMINI_API_KEY', saved_key)
        
        # 既存のキーがある場合は自動的に設定
        if existing_key and not st.session_state.api_key_set:
            if setup_gemini_api(existing_key):
                st.session_state.api_key_set = True
                add_log("保存されたAPI Keyを読み込みました", "INFO")
        
        # API Keyの状態表示
        if st.session_state.api_key_set or existing_key:
            st.success("✅ API Key: 設定済み")
            if st.button("🔑 API Keyを変更", key="change_api_key"):
                st.session_state.show_api_input = True
                st.session_state.api_key_set = False
                st.rerun()
        else:
            st.session_state.show_api_input = True
        
        # API Key入力欄の表示
        if st.session_state.get('show_api_input', False):
            api_key = st.text_input(
                "Gemini API Key",
                value="",
                type="password",
                help="Google AI Studio (https://aistudio.google.com/) で取得したAPI Keyを入力してください",
                key="api_key_input"
            )
            
            if st.button("API Keyを設定", type="primary", key="set_api_key"):
                if api_key:
                    if setup_gemini_api(api_key):
                        st.session_state.api_key_set = True
                        st.session_state.show_api_input = False
                        st.success("✅ API Keyが設定・保存されました")
                        add_log("Gemini API Keyが設定されました", "SUCCESS")
                        st.rerun()
                    else:
                        st.error("❌ API Keyの設定に失敗しました")
                else:
                    st.warning("⚠️ API Keyを入力してください")
        
        st.divider()
        
        # キャラクター管理
        st.header("👤 キャラクター管理")
        if st.button("キャラクターを追加"):
            st.session_state.show_character_upload = True
        
        character_manager = CharacterManager(BASE_DIR)
        characters = character_manager.get_character_list()
        if characters:
            st.write(f"登録済み: {len(characters)}人")
            for char in characters:
                st.caption(f"• {char}")
        else:
            st.info("キャラクターが登録されていません")
        
        if st.session_state.get('show_character_upload', False):
            st.divider()
            st.subheader("キャラクターを追加")
            uploaded_file = st.file_uploader("キャラクター画像をアップロード", type=['png', 'jpg', 'jpeg'])
            char_name = st.text_input("キャラクター名を入力")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("キャンセル"):
                    st.session_state.show_character_upload = False
                    st.rerun()
            with col2:
                if st.button("追加", type="primary"):
                    if uploaded_file and char_name:
                        # 一時ファイルに保存
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = Path(tmp.name)
                        
                        result_path = character_manager.add_character(char_name, tmp_path, uploaded_file)
                        if result_path:
                            st.success(f"✅ {char_name}を追加しました")
                            st.session_state.show_character_upload = False
                            tmp_path.unlink()  # 一時ファイルを削除
                            st.rerun()
                        else:
                            st.error("❌ 追加に失敗しました")
                    else:
                        st.warning("⚠️ 画像と名前を入力してください")
        
        st.divider()
        
        # Watchdog制御（手動開始/停止）
        st.header("📁 フォルダ監視（自動処理）")
        st.info("💡 自動処理は無効化されています。動画処理は「🎬 動画処理」タブから手動で実行してください。")
        
        # 自動処理の有効/無効を選択
        auto_process_enabled = st.checkbox(
            "自動処理を有効にする（推奨: 無効）",
            value=False,
            help="有効にすると、フォルダにファイルが追加された際に自動的に処理が開始されます。"
        )
        
        if auto_process_enabled:
            # 初期起動時に自動的に監視を開始
            if not st.session_state.watchdog_running:
                start_watchdog()
            
            if st.session_state.watchdog_running:
                st.success("🟢 監視中（自動開始）")
                if st.button("監視を停止"):
                    stop_watchdog()
                    st.rerun()
            else:
                st.info("⚪ 停止中")
                if st.button("監視を開始"):
                    start_watchdog()
                    st.rerun()
        else:
            # 自動処理が無効な場合は監視を停止
            if st.session_state.watchdog_running:
                stop_watchdog()
                st.rerun()
            st.info("📝 動画処理は「🎬 動画処理」タブから手動で実行できます。")
    
    # メインエリア
    # フォルダ作成
    created = create_folders()
    if created:
        st.info(f"📁 以下のフォルダを作成しました: {', '.join(created)}")
    
    # 起動時のガイドライン表示
    if not st.session_state.api_key_set and not os.environ.get('GEMINI_API_KEY'):
        st.info("""
        ### 🎯 MVAIアプリケーションが起動しました
        
        監督が行う最初のステップは以下の通りです：
        
        1. **Gemini APIキーを取得し、アプリケーションに入力します**
           - Google AI Studio (https://aistudio.google.com/) にアクセス
           - API Keyを生成し、左側のサイドバーに入力
        
        2. **Suno AIで曲を生成し、[🎶_曲_Input]フォルダに入れます**
           - `C:\\MVAI\\01_曲_Input` フォルダに音声ファイルを配置
           - 自動的にBPMとビートタイミングが解析されます
        
        3. **プロンプト生成アシスタントを使い、Sora/Grok用のプロンプトを作成します**
           - 下記のプロンプト生成セクションをご利用ください
        """)
    
    # タブ構成（主要機能を左側に、補助機能を右端に配置）
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🤖 プロンプト生成", "📝 プロンプト履歴", "🎬 動画処理", "🎵 MV自動生成", "📊 ステータス/ログ", "📁 フォルダ構成"])
    
    # タブ1: プロンプト生成
    with tab1:
        if not st.session_state.api_key_set and not os.environ.get('GEMINI_API_KEY'):
            st.warning("⚠️ まず、サイドバーでGemini API Keyを設定してください")
        else:
            character_manager = CharacterManager(BASE_DIR)
            prompt_generator = PromptGenerator()
            prompt_history = PromptHistory(BASE_DIR)
            
            st.header("🎨 プロンプト生成アシスタント（対話形式）")
            st.caption("対話に従って選択肢を選んでいくだけで、プロンプトが自動的に完成します。")
            
            # プロンプトタイプの選択（最初のステップ）
            if 'prompt_type_selected' not in st.session_state:
                prompt_type = st.radio(
                    "何のプロンプトを作成しますか？",
                    [
                        "🎵 曲を生成するためのプロンプト（Suno AI用）",
                        "🖼️ 動画シーンの基となる画像を作成するプロンプト（Grok Scene用）",
                        "🎬 MVの1シーンを作成するプロンプト（Sora/Grok/Luma用）",
                        "👤 一貫性のあるキャラクター画像を作成するプロンプト（Gemini 3 / Adobe Firefly用）"
                    ],
                    horizontal=False,
                    key="prompt_type_radio"
                )
                
                if st.button("開始", type="primary"):
                    st.session_state.prompt_type_selected = prompt_type
                    st.rerun()
            else:
                prompt_type = st.session_state.prompt_type_selected
                
                # リセットボタン
                if st.button("🔙 最初からやり直す"):
                    del st.session_state.prompt_type_selected
                    if 'prompt_dialog_step' in st.session_state:
                        del st.session_state.prompt_dialog_step
                    if 'prompt_dialog_data' in st.session_state:
                        del st.session_state.prompt_dialog_data
                    st.rerun()
                
                st.divider()
                
                # 対話形式のプロンプト生成
                dialog = None
                if "🎵 曲を生成するためのプロンプト" in prompt_type:
                    dialog = SunoPromptDialog(character_manager)
                elif "🖼️ 動画シーンの基となる画像を作成するプロンプト" in prompt_type:
                    dialog = ImagePromptDialog(character_manager)
                elif "🎬 MVの1シーンを作成するプロンプト" in prompt_type:
                    dialog = VideoPromptDialog(character_manager)
                elif "👤 一貫性のあるキャラクター画像を作成するプロンプト" in prompt_type:
                    dialog = CharacterImageDialog(character_manager)
                
                if dialog:
                    result = dialog.render()
                    
                    if result:
                        # プロンプトをGeminiで改善
                        with st.spinner("プロンプトを最適化中..."):
                            try:
                                if "🎵 曲を生成するためのプロンプト" in prompt_type:
                                    final_prompt = prompt_generator.generate_suno_prompt(result)
                                elif "🖼️ 動画シーンの基となる画像を作成するプロンプト" in prompt_type:
                                    final_prompt = prompt_generator.generate_grok_scene_prompt(result)
                                elif "👤 一貫性のあるキャラクター画像を作成するプロンプト" in prompt_type:
                                    # キャラクター画像生成用はそのまま使用（Geminiで最適化しない）
                                    final_prompt = result
                                    
                                    # キャラクター属性を保存
                                    dialog_data = dialog.get_data()
                                    if dialog_data.get("base_character") or dialog_data.get("character"):
                                        char_name = dialog_data.get("base_character") or dialog_data.get("character")
                                        if char_name:
                                            # 属性を抽出して保存
                                            attributes = {
                                                "character_style": dialog_data.get("character_style"),
                                                "hair_style": dialog_data.get("hair_style"),
                                                "hair_color": dialog_data.get("hair_color"),
                                                "eye_color": dialog_data.get("eye_color"),
                                                "tops": dialog_data.get("tops"),
                                                "bottoms": dialog_data.get("bottoms"),
                                                "onepiece": dialog_data.get("onepiece"),
                                                "outerwear": dialog_data.get("outerwear"),
                                                "socks": dialog_data.get("socks"),
                                                "shoes": dialog_data.get("shoes"),
                                                "wraps": dialog_data.get("wraps"),
                                                "patterns": dialog_data.get("patterns"),
                                                "expression": dialog_data.get("expression"),
                                                "age_range": dialog_data.get("age_range"),
                                                "body_type": dialog_data.get("body_type"),
                                                "accessories": dialog_data.get("accessories")
                                            }
                                            # 空の値を削除
                                            attributes = {k: v for k, v in attributes.items() if v}
                                            character_manager.save_character_attributes(char_name, attributes)
                                            add_log(f"キャラクター属性を保存しました: {char_name}", "INFO")
                                else:
                                    final_prompt = prompt_generator.generate_sora_grok_prompt(result)
                                
                                st.success("✅ プロンプトが生成されました")
                                
                                # nanobanana pro形式の場合はPositive/Negativeを分けて表示
                                positive_part = ""
                                negative_part = ""
                                if "**Positive Prompt:**" in final_prompt and "**Negative Prompt:**" in final_prompt:
                                    parts = final_prompt.split("**Negative Prompt:**")
                                    positive_part = parts[0].replace("**Positive Prompt:**", "").strip()
                                    negative_part = parts[1].strip() if len(parts) > 1 else ""
                                    
                                    st.markdown("### Positive Prompt")
                                    st.code(positive_part, language="text")
                                    
                                    st.markdown("### Negative Prompt")
                                    st.code(negative_part, language="text")
                                    
                                    # コピー用のテキストエリア
                                    st.text_area(
                                        "Positive Prompt（コピー用）",
                                        value=positive_part,
                                        height=100,
                                        key=f"prompt_positive_{datetime.now().timestamp()}"
                                    )
                                    
                                    st.text_area(
                                        "Negative Prompt（コピー用）",
                                        value=negative_part,
                                        height=100,
                                        key=f"prompt_negative_{datetime.now().timestamp()}"
                                    )
                                else:
                                    st.code(final_prompt, language="text")
                                    
                                    # コピー用のテキストエリア
                                    st.text_area(
                                        "生成されたプロンプト（コピー用）",
                                        value=final_prompt,
                                        height=150,
                                        key=f"prompt_result_{datetime.now().timestamp()}"
                                    )
                                
                                # プロンプト履歴に保存
                                dialog_data = dialog.get_data() if dialog else {}
                                prompt_history.add_prompt(
                                    prompt_type=prompt_type,
                                    positive_prompt=positive_part if positive_part else final_prompt,
                                    negative_prompt=negative_part,
                                    dialog_data=dialog_data,
                                    final_prompt=final_prompt
                                    )
                                
                                # プロンプト履歴に保存
                                dialog_data = dialog.get_data() if dialog else {}
                                prompt_history.add_prompt(
                                    prompt_type=prompt_type,
                                    positive_prompt=positive_part if positive_part else final_prompt,
                                    negative_prompt=negative_part,
                                    dialog_data=dialog_data,
                                    final_prompt=final_prompt
                                )
                                
                                # プロンプト生成後も修正可能にする
                                st.divider()
                                if st.button("📝 選択内容を修正する", type="secondary"):
                                    # プロンプト生成状態をリセットせず、対話を再開
                                    if 'prompt_generated' in st.session_state:
                                        del st.session_state.prompt_generated
                                    # 最後のステップに戻る
                                    if dialog:
                                        dialog.set_step(17)  # 追加の指示のステップに戻る
                                    st.rerun()
                                
                                # 活用方法の表示
                                st.info("💡 **次のステップ**: 生成したプロンプトを各AIツールで使用してください。")
                                
                                add_log(f"プロンプト生成完了: {prompt_type}", "SUCCESS")
                            except Exception as e:
                                st.error(f"❌ プロンプト生成に失敗しました: {str(e)}")
                                add_log(f"プロンプト生成エラー: {str(e)}", "ERROR")
    
    # タブ2: プロンプト履歴
    with tab2:
        st.header("📝 プロンプト履歴")
        
        if not st.session_state.api_key_set:
            st.warning("⚠️ まず、サイドバーでGemini API Keyを設定してください")
        else:
            prompt_history = PromptHistory(BASE_DIR)
            history = prompt_history.load_history()
            
            if history:
                st.info(f"📋 {len(history)}件のプロンプト履歴があります")
                
                # 履歴を新しい順に表示
                for i, prompt_data in enumerate(reversed(history[-10:]), 1):
                    with st.expander(f"📝 {prompt_data.get('prompt_type', '不明')} - {prompt_data.get('timestamp', '')}"):
                        st.write("**プロンプトタイプ:**", prompt_data.get('prompt_type', '不明'))
                        st.write("**生成日時:**", prompt_data.get('timestamp', '不明'))
                        
                        if prompt_data.get('positive_prompt'):
                            st.write("**Positive Prompt:**")
                            st.code(prompt_data.get('positive_prompt'), language="text")
                        
                        if prompt_data.get('negative_prompt'):
                            st.write("**Negative Prompt:**")
                            st.code(prompt_data.get('negative_prompt'), language="text")
                        
                        if prompt_data.get('final_prompt'):
                            st.write("**Final Prompt:**")
                            st.code(prompt_data.get('final_prompt'), language="text")
                        
                        if prompt_data.get('dialog_data'):
                            st.write("**選択内容:**")
                            st.json(prompt_data.get('dialog_data'))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"📋 コピー", key=f"copy_{i}"):
                                prompt_to_copy = prompt_data.get('final_prompt') or prompt_data.get('positive_prompt', '')
                                st.code(prompt_to_copy, language="text")
                                st.success("プロンプトをコピーしました")
                        
                        with col2:
                            favorites = prompt_history.load_favorites()
                            is_favorite = any(f.get('id') == prompt_data.get('id') for f in favorites)
                            if is_favorite:
                                if st.button(f"⭐ お気に入りから削除", key=f"unfav_{i}"):
                                    prompt_history.remove_favorite(prompt_data.get('id'))
                                    st.rerun()
                            else:
                                if st.button(f"⭐ お気に入りに追加", key=f"fav_{i}"):
                                    prompt_history.add_favorite(prompt_data)
                                    st.rerun()
            else:
                st.info("まだプロンプト履歴がありません")
            
            st.divider()
            st.subheader("⭐ お気に入りプロンプト")
            favorites = prompt_history.load_favorites()
            if favorites:
                for fav in favorites:
                    with st.expander(f"⭐ {fav.get('prompt_type', '不明')} - {fav.get('timestamp', '')}"):
                        if fav.get('final_prompt'):
                            st.code(fav.get('final_prompt'), language="text")
                        if st.button(f"🗑️ お気に入りから削除", key=f"remove_fav_{fav.get('id')}"):
                            prompt_history.remove_favorite(fav.get('id'))
                            st.rerun()
            else:
                st.info("お気に入りプロンプトがありません")
    
    # タブ3: 動画処理（手動）
    with tab3:
        st.header("🎬 動画処理（手動）")
        
        if not st.session_state.api_key_set:
            st.warning("⚠️ まず、サイドバーでGemini API Keyを設定してください")
        else:
            media_processor = MediaProcessor(BASE_DIR, add_log)
            
            # 処理タイプの選択
            process_type = st.radio(
                "処理タイプを選択してください",
                [
                    "高品質化処理（04_AI動画_生成中 → 05_動画_高品質化）",
                    "リップシンク処理（05_動画_高品質化 → 06_動画_口パク）",
                    "最終処理（06_動画_口パク → 99_MV_編集素材 + XML生成）"
                ],
                key="process_type"
            )
            
            st.divider()
            
            # 処理タイプに応じたフォルダと処理関数を決定
            if "高品質化処理" in process_type:
                source_folder = BASE_DIR / "04_AI動画_生成中"
                process_func = media_processor.trigger_quality_pipeline
                process_name = "高品質化"
            elif "リップシンク処理" in process_type:
                source_folder = BASE_DIR / "05_動画_高品質化"
                process_func = media_processor.process_lipsync
                process_name = "リップシンク"
            else:
                source_folder = BASE_DIR / "06_動画_口パク"
                process_func = media_processor.finalize_assets
                process_name = "最終処理"
            
            # フォルダ内の動画ファイルを取得（再帰的にサブフォルダも検索、使用済み素材フォルダも含む）
            if source_folder.exists():
                video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
                video_files = [
                    f for f in source_folder.rglob("*")
                    if f.is_file() 
                    and f.suffix.lower() in video_extensions
                ]
                
                if video_files:
                    st.info(f"📂 {source_folder.name} フォルダに {len(video_files)} 個の動画ファイルがあります")
                    
                    # サムネイル付きでファイル一覧を表示
                    st.subheader("📹 動画ファイル一覧（サムネイル付き）")
                    
                    # グリッド表示（3列）
                    cols_per_row = 3
                    for row_start in range(0, len(video_files), cols_per_row):
                        cols = st.columns(cols_per_row)
                        row_files = video_files[row_start:row_start + cols_per_row]
                        
                        for idx, video_file in enumerate(row_files):
                            with cols[idx]:
                                # サムネイルを生成（同期的に実行）
                                thumbnail_path = None
                                
                                # サムネイル生成を試行
                                try:
                                    thumbnail_path = media_processor.generate_thumbnail(video_file)
                                except Exception as e:
                                    # エラーは無視して続行
                                    pass
                                
                                # サムネイルを表示
                                if thumbnail_path and thumbnail_path.exists():
                                    try:
                                        file_size = thumbnail_path.stat().st_size
                                        if file_size > 0:
                                            # 画像をバイトデータとして読み込んで表示
                                            with open(thumbnail_path, "rb") as f:
                                                img_bytes = f.read()
                                                st.image(img_bytes, caption=video_file.name, use_container_width=True)
                                        else:
                                            # 空のファイル
                                            st.info(f"📹 {video_file.name}")
                                    except Exception as e:
                                        # 画像読み込みに失敗した場合はファイル名のみ表示
                                        st.info(f"📹 {video_file.name}")
                                else:
                                    # サムネイルが生成されていない場合はファイル名のみ表示
                                    st.info(f"📹 {video_file.name}")
                                
                                # ファイル情報
                                file_size = video_file.stat().st_size / (1024 * 1024)  # MB
                                st.caption(f"{file_size:.1f} MB")
                                
                                # 選択ボタン
                                if st.button(f"選択", key=f"select_{video_file.name}_{row_start}_{idx}"):
                                    st.session_state.selected_video_file = video_file.name
                                    st.rerun()
                    
                    st.divider()
                    
                    # 選択されたファイルを表示
                    selected_file = st.session_state.get("selected_video_file", None)
                    if selected_file:
                        # 選択されたファイルが存在するか確認
                        if not any(f.name == selected_file for f in video_files):
                            selected_file = None
                            st.session_state.selected_video_file = None
                    
                    # ファイル選択（ドロップダウンも残す）
                    file_names = [f.name for f in video_files]
                    if not selected_file and file_names:
                        selected_file = file_names[0]
                    
                    selected_file = st.selectbox(
                        "処理する動画ファイルを選択してください（または上記のサムネイルから選択）",
                        file_names,
                        index=file_names.index(selected_file) if selected_file and selected_file in file_names else 0,
                        key="selected_video_file_dropdown"
                    )
                    
                    # ドロップダウンで選択された場合はセッション状態を更新
                    if selected_file:
                        st.session_state.selected_video_file = selected_file
                    
                    if selected_file:
                        selected_path = source_folder / selected_file
                        
                        # ファイル情報の表示
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("ファイル名", selected_file)
                            file_size = selected_path.stat().st_size / (1024 * 1024)  # MB
                            st.metric("ファイルサイズ", f"{file_size:.2f} MB")
                        
                        with col2:
                            try:
                                import ffmpeg
                                probe = ffmpeg.probe(str(selected_path))
                                video_stream = next((s for s in probe['streams'] if s.get('codec_type') == 'video'), None)
                                if video_stream:
                                    width = video_stream.get('width', 0)
                                    height = video_stream.get('height', 0)
                                    duration = float(probe['format'].get('duration', 0))
                                    st.metric("解像度", f"{width}x{height}")
                                    st.metric("長さ", f"{duration:.1f}秒")
                            except:
                                st.info("動画情報の取得に失敗しました")
                        
                        st.divider()
                        
                        # 処理ボタン
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button(f"🚀 {process_name}処理を実行", type="primary", key="process_button"):
                                with st.spinner(f"{process_name}処理を実行中..."):
                                    try:
                                        process_func(selected_path)
                                        st.success(f"✅ {process_name}処理が完了しました")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                        
                        with col2:
                            if st.button("🔄 ファイル一覧を更新", key="refresh_button"):
                                st.rerun()
                        
                        # 複数ファイルの一括処理
                        st.divider()
                        st.subheader("📦 一括処理")
                        
                        selected_files = st.multiselect(
                            f"一括処理するファイルを選択（複数選択可）",
                            file_names,
                            key="batch_files"
                        )
                        
                        if selected_files:
                            st.info(f"{len(selected_files)} 個のファイルが選択されています")
                            
                            if st.button(f"🚀 選択したファイルを一括{process_name}処理", type="primary", key="batch_process_button"):
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                success_count = 0
                                error_count = 0
                                
                                for idx, file_name in enumerate(selected_files):
                                    file_path = source_folder / file_name
                                    status_text.text(f"処理中: {file_name} ({idx+1}/{len(selected_files)})")
                                    
                                    try:
                                        process_func(file_path)
                                        success_count += 1
                                    except Exception as e:
                                        error_count += 1
                                        add_log(f"一括処理エラー ({file_name}): {str(e)}", "ERROR")
                                    
                                    progress_bar.progress((idx + 1) / len(selected_files))
                                
                                status_text.empty()
                                progress_bar.empty()
                                
                                if error_count == 0:
                                    st.success(f"✅ すべてのファイルの{process_name}処理が完了しました（{success_count}個）")
                                else:
                                    st.warning(f"⚠️ 処理完了: 成功 {success_count}個、エラー {error_count}個")
                                
                                st.rerun()
                else:
                    st.warning(f"⚠️ {source_folder.name} フォルダに動画ファイルがありません")
                    st.info(f"💡 動画ファイルを {source_folder.name} フォルダに配置してください")
            else:
                st.error(f"❌ {source_folder.name} フォルダが存在しません")
                if st.button(f"📁 {source_folder.name} フォルダを作成", key="create_folder_button"):
                    source_folder.mkdir(parents=True, exist_ok=True)
                    st.success(f"✅ {source_folder.name} フォルダを作成しました")
                    st.rerun()
    
    # タブ5: ステータス/ログ
    with tab5:
        st.header("📊 処理ログ")
        
        # ログ表示
        if st.session_state.processing_logs:
            # 最新のログを上から表示
            logs_df = pd.DataFrame(reversed(st.session_state.processing_logs))
            
            for _, log in logs_df.iterrows():
                log_type = log['type']
                if log_type == "SUCCESS":
                    st.success(f"[{log['timestamp']}] {log['message']}")
                elif log_type == "ERROR":
                    st.error(f"[{log['timestamp']}] {log['message']}")
                else:
                    st.info(f"[{log['timestamp']}] {log['message']}")
        else:
            st.info("まだログがありません")
        
        # クリアボタン
        if st.button("ログをクリア"):
            st.session_state.processing_logs = []
            st.rerun()
    
    # タブ6: フォルダ構成
    with tab6:
        st.header("📁 フォルダ構成")
        
        for folder in REQUIRED_FOLDERS:
            folder_path = BASE_DIR / folder
            exists = folder_path.exists()
            status = "✅" if exists else "❌"
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write(f"{status}")
            with col2:
                st.write(f"`{folder_path}`")
                if exists:
                    # 再帰的にファイル数をカウント（サブフォルダも含む）
                    file_count = sum(1 for _ in folder_path.rglob("*") if _.is_file())
                    dir_count = sum(1 for _ in folder_path.rglob("*") if _.is_dir())
                    st.caption(f"{file_count} 個のファイル, {dir_count} 個のフォルダ")
    
    # タブ4: MV自動生成
    with tab4:
        st.header("🎵 MV自動生成")
        
        if not st.session_state.api_key_set:
            st.warning("⚠️ まず、サイドバーでGemini API Keyを設定してください")
        else:
            media_processor = MediaProcessor(BASE_DIR, add_log)
            
            st.markdown("""
            ### MV自動生成機能
            
            複数の動画クリップと音声ファイルから、自動的にMVを生成します。
            
            **機能：**
            - 複数の動画クリップを自動結合
            - 音声トラックを追加
            - 動画と音声の長さを自動調整
            - 解像度とフレームレートを統一
            """)
            
            st.divider()
            
            # 動画クリップの選択
            st.subheader("📹 動画クリップの選択")
            
            # リップシンク使用の確認
            use_lipsync = st.checkbox(
                "リップシンク済み動画を使用する（06_動画_口パクフォルダから選択）",
                value=False,
                key="mv_use_lipsync"
            )
            
            # フォルダを決定
            if use_lipsync:
                clip_folder = BASE_DIR / "06_動画_口パク"
                st.info("💡 リップシンクモード: 06_動画_口パクフォルダから動画を選択します")
            else:
                # 動画クリップのソースフォルダを選択
                clip_source = st.radio(
                    "動画クリップのソースフォルダ",
                    [
                        "04_AI動画_生成中（未処理）",
                        "05_動画_高品質化（高品質化済み）",
                        "06_動画_口パク（リップシンク済み）",
                        "99_MV_編集素材（最終処理済み）"
                    ],
                    key="mv_clip_source"
                )
                
                # フォルダを決定
                if "04_AI動画_生成中" in clip_source:
                    clip_folder = BASE_DIR / "04_AI動画_生成中"
                elif "05_動画_高品質化" in clip_source:
                    clip_folder = BASE_DIR / "05_動画_高品質化"
                elif "06_動画_口パク" in clip_source:
                    clip_folder = BASE_DIR / "06_動画_口パク"
                else:
                    clip_folder = BASE_DIR / "99_MV_編集素材"
            
            # 動画ファイルを取得（再帰的にサブフォルダも検索、使用済み素材フォルダも含む）
            video_files = sorted([
                f for f in clip_folder.rglob("*.mp4")
                if f.is_file()
            ])
            
            if not video_files:
                st.warning(f"⚠️ {clip_folder.name}フォルダに動画ファイルが見つかりません")
            else:
                st.info(f"📁 {len(video_files)}個の動画ファイルが見つかりました")
                
                # 動画クリップを選択（複数選択可能）
                selected_clips = st.multiselect(
                    "MVに使用する動画クリップを選択してください（複数選択可）",
                    [f.name for f in video_files],
                    key="mv_selected_clips"
                )
                
                if selected_clips:
                    selected_clip_paths = [clip_folder / name for name in selected_clips]
                    
                    st.divider()
                    
                    # 音声ファイルの選択
                    st.subheader("🎵 音声ファイルの選択")
                    
                    # 音声ファイルを取得（再帰的にサブフォルダも検索）
                    audio_files = sorted([f for f in (BASE_DIR / "99_MV_編集素材").rglob("*.mp3") if f.is_file()])
                    audio_files.extend(sorted([f for f in (BASE_DIR / "99_MV_編集素材").rglob("*.wav") if f.is_file()]))
                    
                    if not audio_files:
                        st.warning("⚠️ 99_MV_編集素材フォルダに音声ファイルが見つかりません")
                        st.info("💡 ヒント: 01_曲_Inputフォルダに音声ファイルを配置すると、自動的に99_MV_編集素材に移動されます")
                    else:
                        selected_audio = st.selectbox(
                            "使用する音声ファイルを選択してください",
                            [f.name for f in audio_files],
                            key="mv_selected_audio"
                        )
                        
                        if selected_audio:
                            audio_path = BASE_DIR / "99_MV_編集素材" / selected_audio
                            
                            st.divider()
                            
                            # MV生成設定
                            st.subheader("⚙️ MV生成設定")
                            
                            output_filename = st.text_input(
                                "出力ファイル名（拡張子なし）",
                                value=f"MV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                key="mv_output_filename"
                            )
                            
                            sync_to_beat = st.checkbox(
                                "ビートに同期する（シーンの切り替えをビートに合わせる）",
                                value=True,
                                key="mv_sync_to_beat"
                            )
                            
                            use_lipsync = st.checkbox(
                                "リップシンク済み動画を使用する（06_動画_口パクフォルダから選択）",
                                value=False,
                                key="mv_use_lipsync"
                            )
                            
                            st.divider()
                            
                            # MV生成ボタン
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if st.button("🚀 MVを生成", type="primary", key="mv_generate_button"):
                                    if not output_filename:
                                        st.error("❌ 出力ファイル名を入力してください")
                                    else:
                                        # MVは98_MV_完成品フォルダに保存
                                        output_path = BASE_DIR / "98_MV_完成品" / f"{output_filename}.mp4"
                                        
                                        # 同名ファイルが存在する場合は番号を付ける
                                        counter = 1
                                        while output_path.exists():
                                            output_path = BASE_DIR / "98_MV_完成品" / f"{output_filename}({counter}).mp4"
                                            counter += 1
                                        
                                        with st.spinner("MVを生成中... しばらくお待ちください"):
                                            try:
                                                success = media_processor.create_mv_from_clips(
                                                    selected_clip_paths,
                                                    audio_path,
                                                    output_path,
                                                    sync_to_beat=sync_to_beat
                                                )
                                                
                                                if success:
                                                    st.success(f"✅ MV生成が完了しました！")
                                                    st.info(f"📁 保存先: {output_path}")
                                                    st.info(f"💡 MVは「98_MV_完成品」フォルダに保存されました")
                                                    
                                                    # ファイル情報を表示
                                                    if output_path.exists():
                                                        file_size = output_path.stat().st_size / (1024*1024)
                                                        st.metric("ファイルサイズ", f"{file_size:.2f} MB")
                                                        
                                                        # 動画情報を取得
                                                        try:
                                                            import ffmpeg
                                                            probe = ffmpeg.probe(str(output_path))
                                                            video_stream = next((s for s in probe['streams'] if s.get('codec_type') == 'video'), None)
                                                            if video_stream:
                                                                width = video_stream.get('width', 0)
                                                                height = video_stream.get('height', 0)
                                                                duration = float(probe['format'].get('duration', 0))
                                                                st.metric("解像度", f"{width}x{height}")
                                                                st.metric("長さ", f"{duration:.1f}秒")
                                                        except:
                                                            pass
                                                    
                                                    st.rerun()
                                                else:
                                                    st.error("❌ MV生成に失敗しました。ログを確認してください。")
                                            except Exception as e:
                                                st.error(f"❌ MV生成中にエラーが発生しました: {str(e)}")
                                        
                            with col2:
                                if st.button("🔄 リセット", key="mv_reset_button"):
                                    st.rerun()
                            
                            # 選択されたクリップと音声の情報を表示
                            st.divider()
                            st.subheader("📋 選択内容の確認")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**選択された動画クリップ:**")
                                for i, clip_name in enumerate(selected_clips, 1):
                                    st.write(f"{i}. {clip_name}")
                            
                            with col2:
                                st.write("**選択された音声:**")
                                st.write(selected_audio)
                                
                                # ビートデータの確認
                                beat_data = media_processor.load_beat_data(audio_path)
                                if beat_data:
                                    st.write(f"**BPM:** {beat_data['bpm']:.2f}")
                                    st.write(f"**ビート数:** {beat_data['total_beats']}")
                                else:
                                    st.write("⚠️ ビートデータが見つかりません")


if __name__ == "__main__":
    main()

