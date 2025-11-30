"""
対話形式のプロンプト生成ダイアログ
"""

from typing import Dict, List, Optional, Tuple
import streamlit as st
from outfit_selector import OutfitSelector
from pose_background_selector import PoseSelector, BackgroundSelector
from nanobanana_prompt_builder import NanobananaPromptBuilder


class PromptDialog:
    """対話形式のプロンプト生成基底クラス"""
    
    def __init__(self, character_manager):
        self.character_manager = character_manager
        self.step_key = "prompt_dialog_step"
        self.data_key = "prompt_dialog_data"
    
    def get_step(self) -> int:
        """現在のステップを取得"""
        return st.session_state.get(self.step_key, 0)
    
    def set_step(self, step: int):
        """ステップを設定"""
        st.session_state[self.step_key] = step
    
    def get_data(self) -> Dict:
        """対話データを取得"""
        if self.data_key not in st.session_state:
            st.session_state[self.data_key] = {}
        return st.session_state[self.data_key]
    
    def set_data(self, key: str, value):
        """対話データを設定"""
        data = self.get_data()
        data[key] = value
        st.session_state[self.data_key] = data
    
    def reset(self):
        """対話をリセット"""
        st.session_state[self.step_key] = 0
        st.session_state[self.data_key] = {}
    
    def render(self) -> Optional[str]:
        """対話をレンダリング（サブクラスで実装）"""
        raise NotImplementedError
    
    def render_history(self):
        """選択履歴を表示（クリック可能）"""
        data = self.get_data()
        if not data:
            return
        
        st.divider()
        with st.expander("📋 これまでに選択した内容（クリックで変更）", expanded=True):
            history_items = []
            step_map = self._get_step_map()  # 各キーに対応するステップ番号を取得
            
            for idx, (key, value) in enumerate(data.items()):
                if isinstance(value, list):
                    display_value = ', '.join(value) if value else 'なし'
                else:
                    display_value = value if value else 'なし'
                
                step_num = step_map.get(key, None)
                if step_num is not None:
                    # クリック可能なボタンとして表示
                    if st.button(f"📝 {self._get_key_label(key)}: {display_value}", key=f"history_btn_{key}_{idx}"):
                        self.set_step(step_num)
                        st.rerun()
                else:
                    history_items.append(f"**{self._get_key_label(key)}**: {display_value}")
            
            if history_items:
                st.markdown("\n".join(history_items))
    
    def _get_step_map(self) -> Dict[str, int]:
        """各キーに対応するステップ番号を返す（サブクラスで実装）"""
        return {}
    
    def _get_key_label(self, key: str) -> str:
        """キーを日本語ラベルに変換"""
        label_map = {
            'genre': 'ジャンル',
            'tempo': 'テンポ',
            'mood': '雰囲気',
            'additional': '追加の希望',
            'character': 'キャラクター',
            'pose': 'ポーズ・構図',
            'background': '背景',
            'lighting': '照明',
            'time_of_day': '時間帯',
            'movement': 'キャラクターの動き',
            'camera_angle': 'カメラアングル',
            'camera_movement': 'カメラの動き',
            'character_style': 'キャラクタースタイル',
            'hair_style': '髪型',
            'hair_color': '髪色',
            'eye_color': '瞳の色',
            'outfit': '服装',
            'expression': '表情',
            'age_range': '年齢層',
            'body_type': '体型',
            'accessories': 'アクセサリー',
            'base_character': 'ベースキャラクター'
        }
        return label_map.get(key, key)


class SunoPromptDialog(PromptDialog):
    """Suno AI用の対話形式プロンプト生成"""
    
    def render(self) -> Optional[str]:
        step = self.get_step()
        data = self.get_data()
        
        # 履歴を表示
        self.render_history()
        
        if step == 0:
            st.markdown("### ステップ 1/7: 曲のジャンルを選んでください")
            genres = [
                "ポップ", "ロック", "ジャズ", "クラシック", "エレクトロニック", "R&B", "ヒップホップ",
                "カントリー", "フォーク", "レゲエ", "メタル", "パンク", "インディー", "アンビエント",
                "ハウス", "テクノ", "ドラム&ベース", "ダブステップ", "トランス", "チルアウト",
                "ローファイ", "シンセウェイブ", "ニューウェイブ", "ポストロック", "プログレッシブロック",
                "オルタナティブロック", "グランジ", "エモ", "ハードロック", "ヘビーメタル",
                "デスメタル", "ブラックメタル", "パワーメタル", "スラッシュメタル", "スラッジメタル",
                "ドゥームメタル", "フォークロック", "カントリーロック", "ブルースロック", "サイケデリックロック",
                "アシッドジャズ", "フュージョン", "スムースジャズ", "ビバップ", "スウィング",
                "ビッグバンド", "ラテンジャズ", "ボサノバ", "サルサ", "タンゴ", "フラメンコ",
                "ケルト", "ワールドミュージック", "アフリカン", "アジアン", "ミニマル",
                "エクスペリメンタル", "ノイズ", "その他"
            ]
            default_genre = data.get("genre", genres[0])
            genre = st.selectbox(
                "どのようなジャンルの曲にしますか？",
                genres,
                index=genres.index(default_genre) if default_genre in genres else 0,
                key="suno_genre"
            )
            if st.button("次へ", type="primary"):
                self.set_data("genre", genre)
                self.set_step(1)
                st.rerun()
            return None
        
        elif step == 1:
            st.markdown("### ステップ 2/7: 曲のテンポを選んでください")
            tempos = [
                "非常に遅い (40-60 BPM)", "遅い (60-80 BPM)", "ゆっくり (80-100 BPM)",
                "中程度 (100-120 BPM)", "普通 (120-140 BPM)", "速い (140-160 BPM)",
                "とても速い (160-180 BPM)", "超高速 (180-200 BPM)", "指定なし"
            ]
            default_tempo = data.get("tempo", tempos[0])
            tempo = st.selectbox(
                "曲のテンポ（速さ）は？",
                tempos,
                index=tempos.index(default_tempo) if default_tempo in tempos else 0,
                key="suno_tempo"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(0)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("tempo", tempo)
                    self.set_step(2)
                    st.rerun()
            return None
        
        elif step == 2:
            st.markdown("### ステップ 3/7: 曲の雰囲気を選んでください")
            moods = [
                "明るい", "暗い", "エネルギッシュ", "静か", "ロマンチック", "悲しい", "楽しい",
                "神秘的", "ドラマチック", "ノスタルジック", "未来的", "クラシック", "エレガント",
                "力強い", "優しい", "激しい", "穏やか", "不安", "希望に満ちた", "絶望的",
                "勝利の", "敗北の", "緊張感のある", "リラックスした", "興奮した", "落ち着いた",
                "夢幻的", "現実的", "抽象的", "叙情的", "叙事的", "メランコリック", "陽気な",
                "深刻な", "軽快な", "重厚な", "繊細な", "大胆な", "控えめな", "派手な",
                "シンプルな", "複雑な", "洗練された", "原始的な", "現代的", "レトロ", "ビンテージ"
            ]
            default_moods = data.get("mood", [])
            mood = st.multiselect(
                "曲の雰囲気（複数選択可）",
                moods,
                default=default_moods,
                key="suno_mood"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(1)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("mood", mood)
                    self.set_step(3)
                    st.rerun()
            return None
        
        elif step == 3:
            st.markdown("### ステップ 4/7: 主な楽器を選んでください（複数選択可）")
            instruments = [
                "ピアノ", "ギター", "ベース", "ドラム", "バイオリン", "チェロ", "ビオラ", "コントラバス",
                "フルート", "クラリネット", "オーボエ", "ファゴット", "サックス", "トランペット",
                "トロンボーン", "ホルン", "チューバ", "ハープ", "オルガン", "シンセサイザー",
                "エレキギター", "エレキベース", "キーボード", "電子ドラム", "パーカッション",
                "マリンバ", "シロフォン", "ティンパニ", "シンバル", "タンバリン", "カスタネット",
                "アコーディオン", "ハーモニカ", "バンジョー", "マンドリン", "ウクレレ", "シタール",
                "三味線", "琴", "尺八", "太鼓", "その他"
            ]
            default_instruments = data.get("instruments", [])
            instruments_selected = st.multiselect(
                "主な楽器（複数選択可）",
                instruments,
                default=default_instruments,
                key="suno_instruments"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(2)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("instruments", instruments_selected)
                    self.set_step(4)
                    st.rerun()
            return None
        
        elif step == 4:
            st.markdown("### ステップ 5/7: ボーカルスタイルを選んでください（任意）")
            vocal_styles = [
                "指定なし", "ソロボーカル（男性）", "ソロボーカル（女性）", "デュエット", "コーラス",
                "ハーモニー", "ラップ", "スクリーミング", "グロウル", "ウィスパー", "ファルセット",
                "テナー", "バリトン", "バス", "ソプラノ", "メゾソプラノ", "アルト", "カウンターテナー",
                "エレクトロニックボイス", "オートチューン", "ボーカルエフェクト", "その他"
            ]
            default_vocal = data.get("vocal_style", "指定なし")
            vocal_style = st.selectbox(
                "ボーカルスタイル",
                vocal_styles,
                index=vocal_styles.index(default_vocal) if default_vocal in vocal_styles else 0,
                key="suno_vocal"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(3)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("vocal_style", vocal_style)
                    self.set_step(5)
                    st.rerun()
            return None
        
        elif step == 5:
            st.markdown("### ステップ 6/7: 曲の長さと構造を選んでください（任意）")
            lengths = [
                "指定なし", "短い (30秒-1分)", "中程度 (1-2分)", "標準 (2-3分)", "長い (3-5分)", "非常に長い (5分以上)"
            ]
            structures = [
                "指定なし", "イントロ→Aメロ→Bメロ→サビ", "Aメロ→サビ→Aメロ→サビ", "インストゥルメンタル",
                "ボーカル中心", "インストゥルメンタル中心", "その他"
            ]
            default_length = data.get("length", "指定なし")
            default_structure = data.get("structure", "指定なし")
            
            length = st.selectbox(
                "曲の長さ",
                lengths,
                index=lengths.index(default_length) if default_length in lengths else 0,
                key="suno_length"
            )
            structure = st.selectbox(
                "曲の構造",
                structures,
                index=structures.index(default_structure) if default_structure in structures else 0,
                key="suno_structure"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(4)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("length", length)
                    self.set_data("structure", structure)
                    self.set_step(6)
                    st.rerun()
            return None
        
        elif step == 6:
            st.markdown("### ステップ 7/7: 追加の希望を入力してください（任意）")
            additional = st.text_area(
                "その他の希望があれば入力してください",
                height=100,
                placeholder="例: ピアノが主旋律で、ストリングスが入っている。80年代のサウンドを意識",
                value=data.get("additional", ""),
                key="suno_additional"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(5)
                    st.rerun()
            with col2:
                if st.button("✨ プロンプトを生成", type="primary"):
                    self.set_data("additional", additional)
                    # プロンプトを生成
                    prompt_text = self._build_prompt()
                    self.reset()
                    return prompt_text
            return None
        
        return None
    
    def _build_prompt(self) -> str:
        """プロンプトを構築"""
        data = self.get_data()
        parts = []
        
        if data.get("genre"):
            parts.append(f"Genre: {data['genre']}")
        if data.get("tempo") and data['tempo'] != "指定なし":
            parts.append(f"Tempo: {data['tempo']}")
        if data.get("mood"):
            parts.append(f"Mood: {', '.join(data['mood'])}")
        if data.get("instruments"):
            parts.append(f"Instruments: {', '.join(data['instruments'])}")
        if data.get("vocal_style") and data['vocal_style'] != "指定なし":
            parts.append(f"Vocal style: {data['vocal_style']}")
        if data.get("length") and data['length'] != "指定なし":
            parts.append(f"Length: {data['length']}")
        if data.get("structure") and data['structure'] != "指定なし":
            parts.append(f"Structure: {data['structure']}")
        if data.get("additional"):
            parts.append(f"Additional notes: {data['additional']}")
        
        return ", ".join(parts)


class ImagePromptDialog(PromptDialog):
    """静止画生成用の対話形式プロンプト生成"""
    
    def render(self) -> Optional[str]:
        step = self.get_step()
        data = self.get_data()
        characters = self.character_manager.get_character_list()
        
        # 履歴を表示
        self.render_history()
        
        if step == 0:
            st.markdown("### ステップ 1/5: キャラクターを選んでください")
            if not characters:
                st.warning("⚠️ キャラクターが登録されていません。サイドバーからキャラクターを追加してください。")
                if st.button("キャラクター管理に移動"):
                    st.session_state.show_character_management = True
                return None
            
            character = st.selectbox(
                "どのキャラクターが登場しますか？",
                characters,
                key="image_character"
            )
            if st.button("次へ", type="primary"):
                self.set_data("character", character)
                # 既存キャラクターの属性を読み込んでデフォルト値として設定
                attributes = self.character_manager.get_character_attributes(character)
                if attributes:
                    for key, value in attributes.items():
                        self.set_data(key, value)
                self.set_step(1)
                st.rerun()
            return None
        
        elif step == 1:
            st.markdown("### ステップ 2/5: ポーズ・構図を選んでください")
            pose = st.selectbox(
                "キャラクターのポーズ・構図",
                ["正面を向いている", "横を向いている", "後ろを向いている", "座っている", "立っている",
                 "歩いている", "走っている", "踊っている", "手を上げている", "手を振っている",
                 "笑っている", "歌っている", "楽器を演奏している", "その他"],
                key="image_pose"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(0)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("pose", pose)
                    self.set_step(2)
                    st.rerun()
            return None
        
        elif step == 2:
            st.markdown("### ステップ 3/5: 背景を選んでください")
            background = st.selectbox(
                "背景の種類",
                ["桜の木", "森", "公園", "街", "海", "山", "草原", "花畑", "建物内", 
                 "スタジオ", "ステージ", "屋上", "カフェ", "図書館", "学校", "神社",
                 "橋", "川", "湖", "砂漠", "雪景色", "雨", "その他（自由記入）"],
                key="image_background"
            )
            
            background_custom = ""
            if background == "その他（自由記入）":
                background_custom = st.text_input("背景を自由に入力", key="image_background_custom")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(1)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("background", background_custom if background_custom else background)
                    self.set_step(3)
                    st.rerun()
            return None
        
        elif step == 3:
            st.markdown("### ステップ 4/5: 照明・時間帯を選んでください")
            lighting = st.selectbox(
                "照明の種類",
                ["自然光（太陽光）", "柔らかい光", "強い光", "逆光", "サイドライト", 
                 "トップライト（上から）", "ボトムライト（下から）", "スポットライト",
                 "蛍光灯", "電球の光", "キャンドルライト", "ネオンライト", "暗め", "明るめ"],
                key="image_lighting"
            )
            time_of_day = st.selectbox(
                "時間帯",
                ["朝", "昼", "夕方", "夜", "深夜", "日の出", "日の入り", "時間指定なし"],
                key="image_time"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(2)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("lighting", lighting)
                    self.set_data("time_of_day", time_of_day)
                    self.set_step(4)
                    st.rerun()
            return None
        
        elif step == 4:
            st.markdown("### ステップ 5/5: 雰囲気・追加の指示を選んでください")
            mood = st.multiselect(
                "画像の雰囲気（複数選択可）",
                ["明るい", "暗い", "神秘的", "ロマンチック", "エネルギッシュ", "静か", "にぎやか",
                 "悲しい", "楽しい", "ドラマチック", "エレガント", "カジュアル", "フォーマル",
                 "幻想的", "リアル", "ノスタルジック", "未来的", "クラシック"],
                key="image_mood"
            )
            additional = st.text_area(
                "追加の指示（任意）",
                height=80,
                placeholder="例: 春の午後、柔らかい風が吹いている感じ",
                key="image_additional"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(3)
                    st.rerun()
            with col2:
                if st.button("✨ プロンプトを生成", type="primary"):
                    self.set_data("mood", mood)
                    self.set_data("additional", additional)
                    prompt_text = self._build_prompt()
                    self.reset()
                    return prompt_text
            return None
        
        return None
    
    def _build_prompt(self) -> str:
        """プロンプトを構築"""
        data = self.get_data()
        parts = []
        
        if data.get("character"):
            parts.append(f"Character: {data['character']}")
        if data.get("pose"):
            parts.append(f"Pose: {data['pose']}")
        if data.get("background"):
            parts.append(f"Background: {data['background']}")
        if data.get("lighting"):
            parts.append(f"Lighting: {data['lighting']}")
        if data.get("time_of_day") and data['time_of_day'] != "時間指定なし":
            parts.append(f"Time: {data['time_of_day']}")
        if data.get("mood"):
            parts.append(f"Mood: {', '.join(data['mood'])}")
        if data.get("additional"):
            parts.append(f"Additional: {data['additional']}")
        
        return ", ".join(parts)


class VideoPromptDialog(PromptDialog):
    """動画生成用の対話形式プロンプト生成"""
    
    def render(self) -> Optional[str]:
        step = self.get_step()
        data = self.get_data()
        characters = self.character_manager.get_character_list()
        
        # 履歴を表示
        self.render_history()
        
        if step == 0:
            st.markdown("### ステップ 1/6: キャラクターを選んでください")
            if not characters:
                st.warning("⚠️ キャラクターが登録されていません。サイドバーからキャラクターを追加してください。")
                if st.button("キャラクター管理に移動"):
                    st.session_state.show_character_management = True
                return None
            
            character = st.selectbox(
                "どのキャラクターが登場しますか？",
                characters,
                key="video_character"
            )
            if st.button("次へ", type="primary"):
                self.set_data("character", character)
                # 既存キャラクターの属性を読み込んでデフォルト値として設定
                attributes = self.character_manager.get_character_attributes(character)
                if attributes:
                    for key, value in attributes.items():
                        self.set_data(key, value)
                self.set_step(1)
                st.rerun()
            return None
        
        elif step == 1:
            st.markdown("### ステップ 2/6: キャラクターの動きを選んでください")
            movement = st.multiselect(
                "キャラクターの動き（複数選択可）",
                ["静止している", "歩く", "走る", "踊る", "ジャンプ", "回転", "手を振る",
                 "笑う", "歌う", "楽器を演奏", "優雅に動く", "激しく動く", "ゆっくり動く",
                 "ポーズを取る", "振り返る", "手を上げる", "座る", "立つ"],
                key="video_movement"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(0)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("movement", movement)
                    self.set_step(2)
                    st.rerun()
            return None
        
        elif step == 2:
            st.markdown("### ステップ 3/6: カメラワークを選んでください")
            camera_angle = st.selectbox(
                "カメラのアングル",
                ["正面", "斜め前", "横（サイド）", "後ろ", "上から見下ろす", "下から見上げる", 
                 "目線の高さ", "ローアングル", "ハイアングル", "ドローン視点"],
                key="video_camera_angle"
            )
            camera_movement = st.multiselect(
                "カメラの動き（複数選択可）",
                ["固定（動かない）", "ゆっくりズームイン", "ゆっくりズームアウト", "横にパン（左右移動）",
                 "縦にパン（上下移動）", "回転", "フォーカス移動", "トラッキング（被写体を追う）",
                 "ドリー（前後に移動）", "クレーン（上下に移動）"],
                key="video_camera_movement"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(1)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("camera_angle", camera_angle)
                    self.set_data("camera_movement", camera_movement)
                    self.set_step(3)
                    st.rerun()
            return None
        
        elif step == 3:
            st.markdown("### ステップ 4/6: 背景を選んでください")
            background = st.selectbox(
                "背景の種類",
                ["桜の木", "森", "公園", "街", "海", "山", "草原", "花畑", "建物内", 
                 "スタジオ", "ステージ", "屋上", "カフェ", "図書館", "学校", "神社",
                 "橋", "川", "湖", "砂漠", "雪景色", "雨", "その他（自由記入）"],
                key="video_background"
            )
            
            background_custom = ""
            if background == "その他（自由記入）":
                background_custom = st.text_input("背景を自由に入力", key="video_background_custom")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(2)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("background", background_custom if background_custom else background)
                    self.set_step(4)
                    st.rerun()
            return None
        
        elif step == 4:
            st.markdown("### ステップ 5/6: 照明・時間帯を選んでください")
            lighting = st.selectbox(
                "照明の種類",
                ["自然光（太陽光）", "柔らかい光", "強い光", "逆光", "サイドライト", 
                 "トップライト（上から）", "ボトムライト（下から）", "スポットライト",
                 "蛍光灯", "電球の光", "キャンドルライト", "ネオンライト", "暗め", "明るめ"],
                key="video_lighting"
            )
            time_of_day = st.selectbox(
                "時間帯",
                ["朝", "昼", "夕方", "夜", "深夜", "日の出", "日の入り", "時間指定なし"],
                key="video_time"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(3)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("lighting", lighting)
                    self.set_data("time_of_day", time_of_day)
                    self.set_step(5)
                    st.rerun()
            return None
        
        elif step == 5:
            st.markdown("### ステップ 6/6: 雰囲気・追加の指示を選んでください")
            mood = st.multiselect(
                "シーンの雰囲気（複数選択可）",
                ["明るい", "暗い", "神秘的", "ロマンチック", "エネルギッシュ", "静か", "にぎやか",
                 "悲しい", "楽しい", "ドラマチック", "エレガント", "カジュアル", "フォーマル",
                 "幻想的", "リアル", "ノスタルジック", "未来的", "クラシック"],
                key="video_mood"
            )
            additional = st.text_area(
                "追加の指示（任意）",
                height=80,
                placeholder="例: 春の午後、柔らかい風が吹いている感じ",
                key="video_additional"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(4)
                    st.rerun()
            with col2:
                if st.button("✨ プロンプトを生成", type="primary"):
                    self.set_data("mood", mood)
                    self.set_data("additional", additional)
                    prompt_text = self._build_prompt()
                    self.reset()
                    return prompt_text
            return None
        
        return None
    
    def _build_prompt(self) -> str:
        """プロンプトを構築"""
        data = self.get_data()
        parts = []
        
        if data.get("character"):
            parts.append(f"Character: {data['character']}")
        if data.get("movement"):
            parts.append(f"Movement: {', '.join(data['movement'])}")
        if data.get("camera_angle"):
            parts.append(f"Camera angle: {data['camera_angle']}")
        if data.get("camera_movement"):
            parts.append(f"Camera movement: {', '.join(data['camera_movement'])}")
        if data.get("background"):
            parts.append(f"Background: {data['background']}")
        if data.get("lighting"):
            parts.append(f"Lighting: {data['lighting']}")
        if data.get("time_of_day") and data['time_of_day'] != "時間指定なし":
            parts.append(f"Time: {data['time_of_day']}")
        if data.get("mood"):
            parts.append(f"Mood: {', '.join(data['mood'])}")
        if data.get("additional"):
            parts.append(f"Additional: {data['additional']}")
        
        return ", ".join(parts)


class CharacterImageDialog(PromptDialog):
    """キャラクター画像生成用の対話形式プロンプト生成（I2I対応）"""
    
    def _get_step_map(self) -> Dict[str, int]:
        """各キーに対応するステップ番号を返す"""
        return {
            'mode': 0,
            'base_character': 1,
            'character_style': 2,
            'hair_style': 3,
            'hair_color': 4,
            'eye_color': 5,
            'pose': 6,
            'background': 7,
            'outfit_type': 8,
            'tops': 9,
            'bottoms': 10,
            'onepiece': 12,
            'outerwear': 11,
            'socks': 13,
            'shoes': 14,
            'wraps': 15,
            'patterns': 16,
            'expression': 15,
            'age_range': 16,
            'body_type': 16,
            'accessories': 16,
            'additional': 17
        }
    
    def render(self) -> Optional[str]:
        step = self.get_step()
        data = self.get_data()
        characters = self.character_manager.get_character_list()
        
        # 履歴を表示
        self.render_history()
        
        if step == 0:
            st.markdown("### ステップ 1/10: 作成モードを選んでください")
            mode = st.radio(
                "どの方法でキャラクター画像を作成しますか？",
                ["既存のキャラクター画像を元に作成（I2I）", "1から新規に作成"],
                key="char_mode"
            )
            if st.button("次へ", type="primary"):
                self.set_data("mode", mode)
                self.set_step(1)
                st.rerun()
            return None
        
        elif step == 1:
            mode = data.get("mode", "")
            if "既存のキャラクター画像を元に作成" in mode:
                st.markdown("### ステップ 2/10: ベースとなるキャラクターを選んでください")
                if not characters:
                    st.warning("⚠️ キャラクターが登録されていません。サイドバーからキャラクターを追加してください。")
                    if st.button("キャラクター管理に移動"):
                        st.session_state.show_character_management = True
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("戻る"):
                            self.set_step(0)
                            st.rerun()
                    return None
                
                base_character = st.selectbox(
                    "どのキャラクターをベースにしますか？",
                    characters,
                    key="char_base"
                )
                
                # モーダルで画像を表示・ダウンロードできるボタン
                modal_key = f"char_image_modal_{base_character}"
                if st.button("🖼️ キャラクター画像を表示", key=f"show_images_{base_character}"):
                    st.session_state[modal_key] = not st.session_state.get(modal_key, False)
                    st.rerun()
                
                # モーダル表示
                if st.session_state.get(modal_key, False):
                    with st.expander("📁 キャラクター画像一覧", expanded=True):
                        images = self.character_manager.get_character_images(base_character)
                        if images:
                            st.info(f"📂 {base_character}のフォルダ内に{len(images)}枚の画像があります")
                            
                            # グリッド表示（3列）
                            cols = st.columns(3)
                            for idx, img_path in enumerate(images):
                                col = cols[idx % 3]
                                with col:
                                    try:
                                        # 画像を読み込んで表示
                                        from PIL import Image
                                        img = Image.open(img_path)
                                        st.image(img, caption=img_path.name, use_container_width=True)
                                        
                                        # ダウンロードボタン
                                        with open(img_path, "rb") as f:
                                            st.download_button(
                                                label="⬇️ ダウンロード",
                                                data=f.read(),
                                                file_name=img_path.name,
                                                mime="image/png" if img_path.suffix.lower() == '.png' else "image/jpeg",
                                                key=f"download_{img_path.name}_{idx}"
                                            )
                                    except Exception as e:
                                        st.error(f"画像の読み込みエラー: {str(e)}")
                        else:
                            st.warning("このキャラクターの画像が見つかりません")
                        
                        if st.button("❌ 閉じる", key=f"close_modal_{base_character}"):
                            st.session_state[modal_key] = False
                            st.rerun()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("戻る"):
                        self.set_step(0)
                        st.rerun()
                with col2:
                    if st.button("次へ", type="primary"):
                        self.set_data("base_character", base_character)
                        # 既存キャラクターの属性を読み込んでデフォルト値として設定
                        attributes = self.character_manager.get_character_attributes(base_character)
                        if attributes:
                            for key, value in attributes.items():
                                self.set_data(key, value)
                        self.set_step(2)
                        st.rerun()
                return None
            else:
                # 新規作成の場合はスキップ
                self.set_step(2)
                st.rerun()
                return None
        
        elif step == 2:
            st.markdown("### ステップ 3/20: キャラクタースタイルを選んでください")
            # Base characterがある場合は「指定なし(既存のまま)」を追加
            has_base = bool(data.get("base_character"))
            style_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            style_options.extend(["アニメ風", "リアル", "3D", "イラスト", "油絵風", "水彩画風", "デジタルアート", "その他"])
            
            default_style = data.get("character_style", style_options[0])
            default_index = style_options.index(default_style) if default_style in style_options else 0
            
            style = st.selectbox(
                "キャラクターのスタイル",
                style_options,
                index=default_index,
                key="char_style"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("character_style_emphasis", False), key="char_style_emphasis")
            if emphasis:
                self.set_data("character_style_emphasis", True)
            else:
                self.set_data("character_style_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    prev_step = 1 if "既存" in data.get("mode", "") else 0
                    self.set_step(prev_step)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("character_style", style)
                    self.set_step(3)
                    st.rerun()
            return None
        
        elif step == 3:
            st.markdown("### ステップ 4/20: 髪型を選んでください")
            has_base = bool(data.get("base_character"))
            hair_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            hair_options.extend(["ショート", "ボブ", "ロング", "ツインテール", "ポニーテール", "おさげ", "三つ編み",
                               "アップスタイル", "ボリューム", "ストレート", "カール", "ウェーブ", "その他"])
            
            default_hair = data.get("hair_style", hair_options[0])
            default_index = hair_options.index(default_hair) if default_hair in hair_options else 0
            
            hair_style = st.selectbox(
                "髪型",
                hair_options,
                index=default_index,
                key="char_hair_style"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("hair_style_emphasis", False), key="hair_style_emphasis")
            if emphasis:
                self.set_data("hair_style_emphasis", True)
            else:
                self.set_data("hair_style_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(2)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("hair_style", hair_style)
                    self.set_step(4)
                    st.rerun()
            return None
        
        elif step == 4:
            st.markdown("### ステップ 5/20: 髪色を選んでください")
            has_base = bool(data.get("base_character"))
            hair_color_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            hair_color_options.extend(["黒", "茶色", "金", "銀", "白", "赤", "ピンク", "青", "紫", "緑", "オレンジ", "その他"])
            
            default_hair_color = data.get("hair_color", hair_color_options[0])
            default_index = hair_color_options.index(default_hair_color) if default_hair_color in hair_color_options else 0
            
            hair_color = st.selectbox(
                "髪色",
                hair_color_options,
                index=default_index,
                key="char_hair_color"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("hair_color_emphasis", False), key="hair_color_emphasis")
            if emphasis:
                self.set_data("hair_color_emphasis", True)
            else:
                self.set_data("hair_color_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(3)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("hair_color", hair_color)
                    self.set_step(5)
                    st.rerun()
            return None
        
        elif step == 5:
            st.markdown("### ステップ 6/20: 瞳の色を選んでください")
            has_base = bool(data.get("base_character"))
            eye_color_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            eye_color_options.extend(["黒", "茶色", "青", "緑", "紫", "金", "銀", "赤", "ピンク", "その他"])
            
            default_eye_color = data.get("eye_color", eye_color_options[0])
            default_index = eye_color_options.index(default_eye_color) if default_eye_color in eye_color_options else 0
            
            eye_color = st.selectbox(
                "瞳の色",
                eye_color_options,
                index=default_index,
                key="char_eye_color"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("eye_color_emphasis", False), key="eye_color_emphasis")
            if emphasis:
                self.set_data("eye_color_emphasis", True)
            else:
                self.set_data("eye_color_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(4)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("eye_color", eye_color)
                    self.set_step(6)
                    st.rerun()
            return None
        
        elif step == 6:
            st.markdown("### ステップ 7/20: ポーズ・構図を選んでください")
            has_base = bool(data.get("base_character"))
            pose_selector = PoseSelector()
            pose_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            pose_options.extend(pose_selector.POSES)
            
            default_pose = data.get("pose", pose_options[0])
            default_index = pose_options.index(default_pose) if default_pose in pose_options else 0
            
            pose = st.selectbox(
                "ポーズ・構図",
                pose_options,
                index=default_index,
                key="char_pose"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("pose_emphasis", False), key="pose_emphasis")
            if emphasis:
                self.set_data("pose_emphasis", True)
            else:
                self.set_data("pose_emphasis", False)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(5)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("pose", pose)
                    self.set_step(7)  # 背景のステップへ
                    st.rerun()
            return None
        
        elif step == 8:
            st.markdown("### ステップ 8/20: 背景を選んでください")
            has_base = bool(data.get("base_character"))
            bg_selector = BackgroundSelector()
            bg_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            bg_options.extend(bg_selector.BACKGROUNDS)
            
            default_bg = data.get("background", bg_options[0])
            default_index = bg_options.index(default_bg) if default_bg in bg_options else 0
            
            background = st.selectbox(
                "背景",
                bg_options,
                index=default_index,
                key="char_background"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("background_emphasis", False), key="background_emphasis")
            if emphasis:
                self.set_data("background_emphasis", True)
            else:
                self.set_data("background_emphasis", False)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(6)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("background", background)
                    self.set_step(8)
                    st.rerun()
            return None
        
        elif step == 8:
            st.markdown("### ステップ 9/20: 服装のタイプを選んでください")
            outfit_selector = OutfitSelector()
            outfit_type = st.radio(
                "服装のタイプ",
                ["上下別々（トップス+ボトムス）", "ワンピース・ドレス", "その他"],
                key="char_outfit_type"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(7)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("outfit_type", outfit_type)
                    if "上下別々" in outfit_type:
                        self.set_step(9)  # トップス選択へ
                    elif "ワンピース" in outfit_type:
                        self.set_step(12)  # ワンピース選択へ
                    else:
                        self.set_step(15)  # その他へ
                    st.rerun()
            return None
        
        elif step == 9:
            st.markdown("### ステップ 10/20: トップス（上に着るもの）を選んでください")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            tops_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            tops_options.extend(outfit_selector.TOPS)
            
            default_tops = data.get("tops", tops_options[0])
            default_index = tops_options.index(default_tops) if default_tops in tops_options else 0
            
            selected_tops = st.selectbox(
                "トップス",
                tops_options,
                index=default_index,
                key="char_tops"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("tops_emphasis", False), key="tops_emphasis")
            if emphasis:
                self.set_data("tops_emphasis", True)
            else:
                self.set_data("tops_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(8)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("tops", selected_tops)
                    self.set_step(10)
                    st.rerun()
            return None
        
        elif step == 10:
            st.markdown("### ステップ 11/20: ボトムス（下にはくもの）を選んでください")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            bottoms_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            bottoms_options.extend(outfit_selector.BOTTOMS)
            
            default_bottoms = data.get("bottoms", bottoms_options[0])
            default_index = bottoms_options.index(default_bottoms) if default_bottoms in bottoms_options else 0
            
            selected_bottoms = st.selectbox(
                "ボトムス",
                bottoms_options,
                index=default_index,
                key="char_bottoms"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("bottoms_emphasis", False), key="bottoms_emphasis")
            if emphasis:
                self.set_data("bottoms_emphasis", True)
            else:
                self.set_data("bottoms_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(7)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("bottoms", selected_bottoms)
                    self.set_step(9)
                    st.rerun()
            return None
        
        elif step == 11:
            st.markdown("### ステップ 12/20: 上着・アウターを選んでください（任意）")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            outerwear_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            outerwear_options.extend(outfit_selector.OUTERWEAR)
            
            default_outerwear = data.get("outerwear", outerwear_options[0])
            default_index = outerwear_options.index(default_outerwear) if default_outerwear in outerwear_options else 0
            
            selected_outerwear = st.selectbox(
                "上着・アウター",
                outerwear_options,
                index=default_index,
                key="char_outerwear"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("outerwear_emphasis", False), key="outerwear_emphasis")
            if emphasis:
                self.set_data("outerwear_emphasis", True)
            else:
                self.set_data("outerwear_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(8)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("outerwear", selected_outerwear if selected_outerwear != "なし" else "")
                    self.set_step(11)  # 靴下へ
                    st.rerun()
            return None
        
        elif step == 12:
            st.markdown("### ステップ 13/20: ワンピース・ドレスを選んでください")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            onepiece_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            onepiece_options.extend(outfit_selector.ONEPIECE)
            
            default_onepiece = data.get("onepiece", onepiece_options[0])
            default_index = onepiece_options.index(default_onepiece) if default_onepiece in onepiece_options else 0
            
            selected_onepiece = st.selectbox(
                "ワンピース・ドレス",
                onepiece_options,
                index=default_index,
                key="char_onepiece"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("onepiece_emphasis", False), key="onepiece_emphasis")
            if emphasis:
                self.set_data("onepiece_emphasis", True)
            else:
                self.set_data("onepiece_emphasis", False)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(8)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("onepiece", selected_onepiece)
                    self.set_step(13)  # 靴下へ
                    st.rerun()
            return None
        
        elif step == 13:
            st.markdown("### ステップ 14/20: 靴下を選んでください（任意）")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            socks_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            socks_options.extend(outfit_selector.SOCKS)
            
            default_socks = data.get("socks", socks_options[0])
            default_index = socks_options.index(default_socks) if default_socks in socks_options else 0
            
            selected_socks = st.selectbox(
                "靴下",
                socks_options,
                index=default_index,
                key="char_socks"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("socks_emphasis", False), key="socks_emphasis")
            if emphasis:
                self.set_data("socks_emphasis", True)
            else:
                self.set_data("socks_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    prev_step = 9 if data.get("outfit_type") == "上下別々（トップス+ボトムス）" else 10
                    self.set_step(prev_step)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("socks", selected_socks if selected_socks != "なし" else "")
                    self.set_step(12)
                    st.rerun()
            return None
        
        elif step == 12:
            st.markdown("### ステップ 12/15: 靴を選んでください（任意）")
            outfit_selector = OutfitSelector()
            shoes = ["なし"] + outfit_selector.SHOES
            default_shoes = data.get("shoes", "なし")
            selected_shoes = st.selectbox(
                "靴",
                shoes,
                index=shoes.index(default_shoes) if default_shoes in shoes else 0,
                key="char_shoes"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(11)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("shoes", selected_shoes if selected_shoes != "なし" else "")
                    self.set_step(13)
                    st.rerun()
            return None
        
        elif step == 15:
            st.markdown("### ステップ 16/20: マント・ストールなどの羽織るものを選んでください（任意）")
            has_base = bool(data.get("base_character"))
            outfit_selector = OutfitSelector()
            wraps_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            wraps_options.extend(outfit_selector.WRAPS)
            
            default_wraps = data.get("wraps", wraps_options[0])
            default_index = wraps_options.index(default_wraps) if default_wraps in wraps_options else 0
            
            selected_wraps = st.selectbox(
                "羽織るもの",
                wraps_options,
                index=default_index,
                key="char_wraps"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("wraps_emphasis", False), key="wraps_emphasis")
            if emphasis:
                self.set_data("wraps_emphasis", True)
            else:
                self.set_data("wraps_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(12)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("wraps", selected_wraps if selected_wraps != "なし" else "")
                    self.set_step(14)
                    st.rerun()
            return None
        
        elif step == 14:
            st.markdown("### ステップ 14/15: 服の柄を選んでください（任意）")
            outfit_selector = OutfitSelector()
            patterns = ["なし"] + outfit_selector.PATTERNS
            default_patterns = data.get("patterns", "なし")
            selected_patterns = st.multiselect(
                "服の柄（複数選択可）",
                outfit_selector.PATTERNS,
                default=[p for p in outfit_selector.PATTERNS if p in (data.get("patterns", []) if isinstance(data.get("patterns"), list) else [])],
                key="char_patterns"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(13)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("patterns", selected_patterns)
                    self.set_step(15)  # 表情へ
                    st.rerun()
            return None
        
        elif step == 15:
            st.markdown("### ステップ 15/20: 表情を選んでください")
            has_base = bool(data.get("base_character"))
            expr_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            expr_options.extend(["笑顔", "無表情", "困った顔", "驚いた顔", "怒った顔", "悲しい顔", "眠そう", "ウインク",
                               "照れた", "真剣", "優しい", "クール", "その他"])
            
            default_expr = data.get("expression", expr_options[0])
            default_index = expr_options.index(default_expr) if default_expr in expr_options else 0
            
            expression = st.selectbox(
                "表情",
                expr_options,
                index=default_index,
                key="char_expression"
            )
            
            # 強調オプション
            emphasis = st.checkbox("この項目を強調する", value=data.get("expression_emphasis", False), key="expression_emphasis")
            if emphasis:
                self.set_data("expression_emphasis", True)
            else:
                self.set_data("expression_emphasis", False)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(14)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("expression", expression)
                    self.set_step(16)
                    st.rerun()
            return None
        
        elif step == 16:
            st.markdown("### ステップ 16/20: その他の要素を選んでください")
            has_base = bool(data.get("base_character"))
            
            age_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            age_options.extend(["幼児", "小学生", "中学生", "高校生", "大学生", "20代", "30代", "40代", "50代以上"])
            default_age = data.get("age_range", age_options[0])
            default_age_index = age_options.index(default_age) if default_age in age_options else 0
            
            age_range = st.selectbox(
                "年齢層",
                age_options,
                index=default_age_index,
                key="char_age"
            )
            
            body_options = ["指定なし(既存のまま)"] if has_base else ["指定なし"]
            body_options.extend(["細身", "普通", "ぽっちゃり", "筋肉質"])
            default_body = data.get("body_type", body_options[0])
            default_body_index = body_options.index(default_body) if default_body in body_options else 0
            
            body_type = st.selectbox(
                "体型",
                body_options,
                index=default_body_index,
                key="char_body"
            )
            
            outfit_selector = OutfitSelector()
            accessories = st.multiselect(
                "アクセサリー（複数選択可）",
                outfit_selector.ACCESSORIES,
                default=[a for a in outfit_selector.ACCESSORIES if a in (data.get("accessories", []) if isinstance(data.get("accessories"), list) else [])],
                key="char_accessories"
            )
            
            # アクセサリーの強調オプション
            accessories_emphasis = st.checkbox("アクセサリーを強調する", value=data.get("accessories_emphasis", False), key="accessories_emphasis")
            if accessories_emphasis:
                self.set_data("accessories_emphasis", True)
            else:
                self.set_data("accessories_emphasis", False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(15)
                    st.rerun()
            with col2:
                if st.button("次へ", type="primary"):
                    self.set_data("age_range", age_range)
                    self.set_data("body_type", body_type)
                    self.set_data("accessories", accessories)
                    self.set_step(17)
                    st.rerun()
            return None
        
        elif step == 17:
            st.markdown("### ステップ 18/20: 追加の指示を入力してください（任意）")
            additional = st.text_area(
                "その他の希望があれば入力してください",
                height=100,
                placeholder="例: 背景はシンプルに、上半身のみ",
                key="char_additional"
            )
            
            # 活用方法の説明を表示
            mode = data.get("mode", "")
            if "既存のキャラクター画像を元に作成" in mode:
                st.info("""
                **📖 このプロンプトの使い方（I2I - Image to Image）**
                
                #### **Option 1: Adobe Firefly**
                1. [Adobe Firefly](https://firefly.adobe.com/) にアクセス
                2. 「Generate image」をクリック
                3. 「Reference image」に、ベースとなるキャラクター画像をアップロード
                4. プロンプト欄に生成したプロンプトをコピー＆ペースト
                5. 「Generate」をクリック
                6. 生成された画像をダウンロード
                
                #### **Option 2: Gemini（ブラウザ/アプリ）**
                1. [Google Gemini](https://gemini.google.com/) にアクセス、またはGeminiアプリを開く
                2. 画像をアップロード（ベースキャラクター画像）
                3. 「この画像を元に、以下のプロンプトで画像を生成してください」と入力
                4. 生成したプロンプトをコピー＆ペースト
                5. 生成された画像をダウンロード
                """)
            else:
                st.info("""
                **📖 このプロンプトの使い方（新規作成）**
                
                #### **Option 1: Adobe Firefly**
                1. [Adobe Firefly](https://firefly.adobe.com/) にアクセス
                2. 「Generate image」をクリック
                3. プロンプト欄に生成したプロンプトをコピー＆ペースト
                4. 「Generate」をクリック
                5. 生成された画像をダウンロード
                
                #### **Option 2: Gemini（ブラウザ/アプリ）**
                1. [Google Gemini](https://gemini.google.com/) にアクセス、またはGeminiアプリを開く
                2. 生成したプロンプトをコピー＆ペースト
                3. 「このプロンプトで画像を生成してください」と入力
                4. 生成された画像をダウンロード
                """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    self.set_step(8)
                    st.rerun()
            with col2:
                if st.button("✨ プロンプトを生成", type="primary"):
                    self.set_data("additional", additional)
                    prompt_text = self._build_prompt()
                    self.reset()
                    return prompt_text
            return None
        
        return None
    
    def _build_prompt(self) -> str:
        """nanobanana pro向けプロンプトを構築"""
        data = self.get_data()
        base_character = data.get("base_character")
        
        # Positive Promptを構築
        positive_prompt = NanobananaPromptBuilder.build_positive_prompt(data, base_character)
        
        # Negative Promptを構築
        negative_prompt = NanobananaPromptBuilder.build_negative_prompt()
        
        # 2つのプロンプトを返す（改行で区切る）
        return f"**Positive Prompt:**\n{positive_prompt}\n\n**Negative Prompt:**\n{negative_prompt}"
