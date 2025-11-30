"""
メディア処理パイプライン
librosa、ffmpeg-pythonを使用した音声・動画処理
"""

import os
import librosa
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess
import ffmpeg
from datetime import datetime
import shutil
from PIL import Image
import tempfile
from typing import Optional, List


class MediaProcessor:
    """メディアファイル処理クラス"""
    
    def __init__(self, base_dir: Path, log_callback=None):
        self.base_dir = base_dir
        self.log_callback = log_callback if log_callback else lambda msg, typ="INFO": None
        
        # フォルダパスの定義
        self.input_audio_dir = base_dir / "01_曲_Input"
        self.input_video_dir = base_dir / "02_元動画_Sora"
        self.still_images_dir = base_dir / "03_静止画_選定"
        self.ai_video_dir = base_dir / "04_AI動画_生成中"
        self.hq_video_dir = base_dir / "05_動画_高品質化"
        self.lipsync_video_dir = base_dir / "06_動画_口パク"
        self.final_assets_dir = base_dir / "99_MV_編集素材"
        self.mv_output_dir = base_dir / "98_MV_完成品"
        self.logs_dir = base_dir / "99_Logs"
        
        # ログフォルダの作成
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.still_images_dir.mkdir(parents=True, exist_ok=True)
        self.hq_video_dir.mkdir(parents=True, exist_ok=True)
        self.lipsync_video_dir.mkdir(parents=True, exist_ok=True)
        self.final_assets_dir.mkdir(parents=True, exist_ok=True)
        self.mv_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用済み素材フォルダの作成
        (self.ai_video_dir / "使用済み素材").mkdir(parents=True, exist_ok=True)
        (self.hq_video_dir / "使用済み素材").mkdir(parents=True, exist_ok=True)
        (self.lipsync_video_dir / "使用済み素材").mkdir(parents=True, exist_ok=True)
        
        # 99_MV_編集素材のサブフォルダ作成（音声ファイル用）
        (self.final_assets_dir / "音声ファイル").mkdir(parents=True, exist_ok=True)
    
    def process_audio_file(self, file_path: Path):
        """
        音声ファイルの処理（BPMとビートタイミング解析）
        
        Args:
            file_path: 処理する音声ファイルのパス
        """
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.log_callback(f"ファイルが見つかりません: {file_path.name}", "ERROR")
                return
            
            # ファイルサイズの確認（空ファイルのチェック）
            if file_path.stat().st_size == 0:
                self.log_callback(f"空のファイルです: {file_path.name}", "ERROR")
                return
            
            self.log_callback(f"音声ファイルの処理を開始: {file_path.name}", "INFO")
            
            # 音声ファイルの読み込み
            try:
                y, sr = librosa.load(str(file_path), sr=None)
            except Exception as e:
                self.log_callback(f"音声ファイルの読み込みに失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            if len(y) == 0:
                self.log_callback(f"音声データが空です: {file_path.name}", "ERROR")
                return
            
            # BPMの計算
            try:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                bpm = float(tempo)
            except Exception as e:
                self.log_callback(f"BPM計算に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # ビートタイミングの取得（秒単位）
            beat_times = librosa.frames_to_time(beats, sr=sr)
            
            # 結果をDataFrameに格納
            df = pd.DataFrame({
                'beat_time_seconds': beat_times,
                'beat_index': range(len(beat_times))
            })
            
            # CSVファイル名の生成（元のファイル名から拡張子を除く）
            song_name = file_path.stem
            csv_filename = f"{song_name}_beats.csv"
            csv_path = self.logs_dir / csv_filename
            
            # CSVファイルに保存
            try:
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            except Exception as e:
                self.log_callback(f"CSV保存に失敗しました ({csv_filename}): {str(e)}", "ERROR")
                return
            
            self.log_callback(
                f"音声解析完了: BPM={bpm:.2f}, ビート数={len(beat_times)}, CSV={csv_filename}",
                "SUCCESS"
            )
            
            # 処理済みファイルを99_MV_編集素材/音声ファイルに移動
            try:
                audio_subdir = self.final_assets_dir / "音声ファイル"
                dest_path = audio_subdir / file_path.name
                # 同名ファイルが存在する場合は番号を付ける
                counter = 1
                while dest_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    dest_path = audio_subdir / f"{stem}({counter}){suffix}"
                    counter += 1
                
                shutil.move(str(file_path), str(dest_path))
                self.log_callback(f"ファイルを移動しました: {dest_path.name}", "INFO")
            except Exception as e:
                self.log_callback(f"ファイル移動に失敗しました ({file_path.name}): {str(e)}", "ERROR")
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log_callback(f"音声処理エラー ({file_path.name}): {str(e)}\n{error_detail}", "ERROR")
    
    def process_video_file(self, file_path: Path):
        """
        動画ファイルの処理（シーンチェンジ検出と静止画抽出）
        
        Args:
            file_path: 処理する動画ファイルのパス
        """
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.log_callback(f"ファイルが見つかりません: {file_path.name}", "ERROR")
                return
            
            # ファイルサイズの確認（空ファイルのチェック）
            if file_path.stat().st_size == 0:
                self.log_callback(f"空のファイルです: {file_path.name}", "ERROR")
                return
            
            self.log_callback(f"動画ファイルの処理を開始: {file_path.name}", "INFO")
            
            # 動画情報の取得
            try:
                probe = ffmpeg.probe(str(file_path))
            except Exception as e:
                self.log_callback(f"動画情報の取得に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # ビデオストリームの検索
            video_info = None
            for stream in probe.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_info = stream
                    break
            
            if video_info is None:
                self.log_callback(f"動画ストリームが見つかりません: {file_path.name}", "ERROR")
                return
            
            # 動画の長さを取得
            try:
                duration = float(probe['format'].get('duration', 0))
                if duration <= 0:
                    self.log_callback(f"動画の長さが無効です: {file_path.name}", "ERROR")
                    return
            except (KeyError, ValueError, TypeError) as e:
                self.log_callback(f"動画の長さの取得に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # FPSの計算（分数形式 "30/1" などを処理）
            r_frame_rate = video_info.get('r_frame_rate', '30/1')
            try:
                if '/' in r_frame_rate:
                    numerator, denominator = map(int, r_frame_rate.split('/'))
                    fps = numerator / denominator if denominator > 0 else 30.0
                else:
                    fps = float(r_frame_rate) if r_frame_rate else 30.0
            except (ValueError, TypeError):
                fps = 30.0  # デフォルト値
            
            # シーンチェンジ検出と動きの大きい箇所を検出
            # 簡易実装: 等間隔でサンプリングし、最大10枚を抽出
            num_frames = min(10, max(1, int(duration * fps / 10)))  # 10秒ごとに1フレーム
            
            # 抽出するタイムスタンプを計算
            timestamps = np.linspace(0, duration, num_frames, endpoint=False)
            
            # 各タイムスタンプで静止画を抽出
            video_name = file_path.stem
            extracted_count = 0
            
            for i, timestamp in enumerate(timestamps):
                try:
                    output_filename = f"{video_name}_frame_{i+1:03d}.jpg"
                    output_path = self.still_images_dir / output_filename
                    
                    # 同名ファイルが存在する場合は番号を付ける
                    counter = 1
                    while output_path.exists():
                        output_filename = f"{video_name}_frame_{i+1:03d}({counter}).jpg"
                        output_path = self.still_images_dir / output_filename
                        counter += 1
                    
                    # ffmpegでフレーム抽出
                    (
                        ffmpeg
                        .input(str(file_path), ss=timestamp)
                        .output(str(output_path), vframes=1, q=2)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    if output_path.exists():
                        extracted_count += 1
                    
                except Exception as e:
                    self.log_callback(f"フレーム抽出エラー (t={timestamp:.2f}s): {str(e)}", "ERROR")
                    continue
            
            if extracted_count > 0:
                self.log_callback(
                    f"動画処理完了: {extracted_count}枚の静止画を抽出しました",
                    "SUCCESS"
                )
            else:
                self.log_callback(
                    f"動画処理完了: 静止画の抽出に失敗しました",
                    "ERROR"
                )
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log_callback(f"動画処理エラー ({file_path.name}): {str(e)}\n{error_detail}", "ERROR")
    
    def trigger_quality_pipeline(self, file_path: Path):
        """
        高品質化パイプライン（Upscale/補間）
        
        04_AI動画_生成中フォルダにファイルが追加された際に呼び出されます。
        FFmpegを使用した簡易的な高品質化処理を実行し、05_動画_高品質化に出力します。
        
        Args:
            file_path: 処理する動画ファイルのパス
        """
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.log_callback(f"ファイルが見つかりません: {file_path.name}", "ERROR")
                return
            
            if file_path.stat().st_size == 0:
                self.log_callback(f"空のファイルです: {file_path.name}", "ERROR")
                return
            
            self.log_callback(f"高品質化処理を開始: {file_path.name}", "INFO")
            
            # 動画情報の取得
            try:
                probe = ffmpeg.probe(str(file_path))
            except Exception as e:
                self.log_callback(f"動画情報の取得に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # ビデオストリームの検索
            video_info = None
            for stream in probe.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_info = stream
                    break
            
            if video_info is None:
                self.log_callback(f"動画ストリームが見つかりません: {file_path.name}", "ERROR")
                return
            
            # 出力ファイル名の生成
            video_name = file_path.stem
            output_filename = f"{video_name}_hq{file_path.suffix}"
            output_path = self.hq_video_dir / output_filename
            
            # 同名ファイルが存在する場合は番号を付ける
            counter = 1
            while output_path.exists():
                output_filename = f"{video_name}_hq({counter}){file_path.suffix}"
                output_path = self.hq_video_dir / output_filename
                counter += 1
            
            # FFmpegを使用した高品質化処理
            # 1. 解像度のアップスケール（2倍、または元の解像度を維持）
            # 2. ビットレートの向上
            # 3. フレームレートの補間
            
            try:
                # 元の解像度を取得
                width = int(video_info.get('width', 1920))
                height = int(video_info.get('height', 1080))
                
                # 元のフレームレートを取得
                r_frame_rate = video_info.get('r_frame_rate', '30/1')
                try:
                    if '/' in r_frame_rate:
                        numerator, denominator = map(int, r_frame_rate.split('/'))
                        original_fps = numerator / denominator if denominator > 0 else 30.0
                    else:
                        original_fps = float(r_frame_rate) if r_frame_rate else 30.0
                except (ValueError, TypeError):
                    original_fps = 30.0
                
                # 2倍アップスケール（最大4Kまで）
                target_width = min(width * 2, 3840)
                target_height = min(height * 2, 2160)
                
                # アスペクト比を維持
                aspect_ratio = width / height
                if target_width / target_height > aspect_ratio:
                    target_width = int(target_height * aspect_ratio)
                else:
                    target_height = int(target_width / aspect_ratio)
                
                # 偶数に調整（エンコーダーの要件）
                target_width = target_width - (target_width % 2)
                target_height = target_height - (target_height % 2)
                
                # 目標フレームレートを決定
                # 30fps以下なら60fpsに、それ以上ならそのまま（最大60fps）
                if original_fps <= 30:
                    target_fps = 60
                elif original_fps <= 60:
                    target_fps = 60  # 60fpsを上限とする
                else:
                    target_fps = original_fps  # 既に高フレームレートの場合はそのまま
                
                self.log_callback(
                    f"アップスケール: {width}x{height} → {target_width}x{target_height}",
                    "INFO"
                )
                
                if target_fps > original_fps:
                    self.log_callback(
                        f"フレームレート補間: {original_fps:.2f}fps → {target_fps}fps",
                        "INFO"
                    )
                else:
                    self.log_callback(
                        f"フレームレート: {original_fps:.2f}fps（補間なし）",
                        "INFO"
                    )
                
                # 出力パスをログに記録
                self.log_callback(
                    f"出力先: {output_path}",
                    "INFO"
                )
                
                # 出力フォルダが存在することを確認
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # FFmpegで高品質化処理
                try:
                    # 入力ストリームを取得
                    input_stream = ffmpeg.input(str(file_path))
                    
                    # スケーリング
                    scaled = input_stream.filter('scale', target_width, target_height)
                    
                    # フレームレート補間（必要に応じて）
                    if target_fps > original_fps:
                        # minterpolateフィルターを使用（モーションベース補間）
                        # mi_mode=mci: モーションベース補間（高品質）
                        # mc_mode=aobmc: 適応的オーバーラップブロックモーション補償
                        # vsbmc=1: 可変サイズブロックモーション補償
                        interpolated = scaled.filter(
                            'minterpolate',
                            fps=target_fps,
                            mi_mode='mci',  # Motion Compensation Interpolation
                            mc_mode='aobmc',  # Adaptive Overlapped Block Motion Compensation
                            vsbmc=1  # Variable-size block motion compensation
                        )
                        video_stream = interpolated
                    else:
                        video_stream = scaled
                    
                    # エンコード設定
                    (
                        video_stream
                        .output(
                            str(output_path),
                            vcodec='libx264',
                            preset='slow',  # 高品質プリセット
                            crf=18,  # 高品質（18-23が推奨、低いほど高品質）
                            pix_fmt='yuv420p',
                            movflags='faststart',  # Web再生最適化
                            r=target_fps  # 出力フレームレートを明示的に指定
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # ファイル生成を待つ（最大5秒）
                    import time
                    wait_time = 0
                    max_wait = 5
                    while not output_path.exists() and wait_time < max_wait:
                        time.sleep(0.5)
                        wait_time += 0.5
                    
                    # 生成されたファイルを確認
                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        if file_size > 0:
                            self.log_callback(
                                f"✅ 高品質化処理完了: {output_path.name} ({file_size / (1024*1024):.2f} MB)",
                                "SUCCESS"
                            )
                            self.log_callback(
                                f"保存先: {output_path}",
                                "INFO"
                            )
                            
                            # 元のファイルを「使用済み素材」フォルダに移動（使用済み素材フォルダの動画は移動しない）
                            if "使用済み素材" not in file_path.parts:
                                try:
                                    used_dir = self.ai_video_dir / "使用済み素材"
                                    used_path = used_dir / file_path.name
                                    counter = 1
                                    while used_path.exists():
                                        stem = file_path.stem
                                        suffix = file_path.suffix
                                        used_path = used_dir / f"{stem}({counter}){suffix}"
                                        counter += 1
                                    if file_path.exists():
                                        shutil.move(str(file_path), str(used_path))
                                        self.log_callback(f"元ファイルを移動しました: {used_path.name}", "INFO")
                                except Exception as e:
                                    self.log_callback(f"元ファイルの移動に失敗しました: {str(e)}", "WARNING")
                            else:
                                self.log_callback(f"使用済み素材フォルダの動画のため、移動しません", "INFO")
                        else:
                            self.log_callback(
                                f"❌ 高品質化処理に失敗しました: ファイルサイズが0です ({file_path.name})",
                                "ERROR"
                            )
                            # 空のファイルを削除
                            if output_path.exists():
                                output_path.unlink()
                    else:
                        self.log_callback(
                            f"❌ 高品質化処理に失敗しました: ファイルが生成されませんでした ({file_path.name})",
                            "ERROR"
                        )
                        self.log_callback(
                            f"期待された出力パス: {output_path}",
                            "ERROR"
                        )
                except ffmpeg.Error as e:
                    error_msg = ""
                    if e.stderr:
                        try:
                            error_msg = e.stderr.decode('utf-8', errors='ignore')
                        except:
                            error_msg = str(e.stderr)
                    else:
                        error_msg = str(e)
                    self.log_callback(
                        f"❌ 高品質化処理エラー ({file_path.name}): {error_msg[:500]}",
                        "ERROR"
                    )
                    # 部分的なファイルが残っている可能性があるので削除
                    if output_path.exists():
                        try:
                            output_path.unlink()
                        except:
                            pass
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    self.log_callback(
                        f"❌ 高品質化処理エラー ({file_path.name}): {str(e)}\n{error_detail[:500]}",
                        "ERROR"
                    )
                    # 部分的なファイルが残っている可能性があるので削除
                    if output_path.exists():
                        try:
                            output_path.unlink()
                        except:
                            pass
                    
            except Exception as e:
                self.log_callback(f"FFmpeg処理エラー ({file_path.name}): {str(e)}", "ERROR")
                return
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log_callback(
                f"高品質化パイプラインエラー ({file_path.name}): {str(e)}\n{error_detail}",
                "ERROR"
            )
    
    def process_lipsync(self, file_path: Path):
        """
        リップシンク処理
        
        05_動画_高品質化フォルダにファイルが追加された際に呼び出されます。
        リップシンク処理を実行し、06_動画_口パクに出力します。
        
        Args:
            file_path: 処理する動画ファイルのパス
        """
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.log_callback(f"ファイルが見つかりません: {file_path.name}", "ERROR")
                return
            
            if file_path.stat().st_size == 0:
                self.log_callback(f"空のファイルです: {file_path.name}", "ERROR")
                return
            
            self.log_callback(f"リップシンク処理を開始: {file_path.name}", "INFO")
            
            # 出力ファイル名の生成
            video_name = file_path.stem
            output_filename = f"{video_name}_lipsync{file_path.suffix}"
            output_path = self.lipsync_video_dir / output_filename
            
            # 同名ファイルが存在する場合は番号を付ける
            counter = 1
            while output_path.exists():
                output_filename = f"{video_name}_lipsync({counter}){file_path.suffix}"
                output_path = self.lipsync_video_dir / output_filename
                counter += 1
            
            # リップシンク処理の実装
            # 注意: 実際のリップシンク処理には専用ツール（Wav2Lip、SadTalker等）が必要です
            # ここではプレースホルダーとして、ファイルをコピーしてメタデータを追加します
            
            try:
                # 現在は簡易実装：ファイルをコピー
                # 実際のリップシンク処理を実装する場合は、以下のツールを統合してください：
                # - Wav2Lip: https://github.com/Rudrabha/Wav2Lip
                # - SadTalker: https://github.com/OpenTalker/SadTalker
                # - LivePortrait: https://github.com/KwaiVGI/LivePortrait
                
                shutil.copy2(str(file_path), str(output_path))
                
                if output_path.exists():
                    self.log_callback(
                        f"リップシンク処理完了: {output_path.name} "
                        "(現在はコピー処理のみ。実際のリップシンク処理を実装する場合は、"
                        "Wav2LipやSadTalkerなどのツールを統合してください)",
                        "SUCCESS"
                    )
                    
                    # 元のファイルを「使用済み素材」フォルダに移動（使用済み素材フォルダの動画は移動しない）
                    if "使用済み素材" not in file_path.parts:
                        try:
                            used_dir = self.hq_video_dir / "使用済み素材"
                            used_path = used_dir / file_path.name
                            counter = 1
                            while used_path.exists():
                                stem = file_path.stem
                                suffix = file_path.suffix
                                used_path = used_dir / f"{stem}({counter}){suffix}"
                                counter += 1
                            shutil.move(str(file_path), str(used_path))
                            self.log_callback(f"元ファイルを移動しました: {used_path.name}", "INFO")
                        except Exception as e:
                            self.log_callback(f"元ファイルの移動に失敗しました: {str(e)}", "WARNING")
                    else:
                        self.log_callback(f"使用済み素材フォルダの動画のため、移動しません", "INFO")
                else:
                    self.log_callback(
                        f"リップシンク処理に失敗しました: {file_path.name}",
                        "ERROR"
                    )
                    
            except Exception as e:
                self.log_callback(f"リップシンク処理エラー ({file_path.name}): {str(e)}", "ERROR")
                return
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log_callback(
                f"リップシンク処理エラー ({file_path.name}): {str(e)}\n{error_detail}",
                "ERROR"
            )
    
    def finalize_assets(self, file_path: Path):
        """
        最終素材処理とXML生成
        
        06_動画_口パクフォルダにファイルが追加された際に呼び出されます。
        最終処理を行い、99_MV_編集素材に移動し、XMLメタデータを生成します。
        
        Args:
            file_path: 処理する動画ファイルのパス
        """
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.log_callback(f"ファイルが見つかりません: {file_path.name}", "ERROR")
                return
            
            if file_path.stat().st_size == 0:
                self.log_callback(f"空のファイルです: {file_path.name}", "ERROR")
                return
            
            self.log_callback(f"最終処理を開始: {file_path.name}", "INFO")
            
            # 動画情報の取得
            try:
                probe = ffmpeg.probe(str(file_path))
            except Exception as e:
                self.log_callback(f"動画情報の取得に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # ビデオストリームの検索
            video_info = None
            audio_info = None
            for stream in probe.get('streams', []):
                if stream.get('codec_type') == 'video' and video_info is None:
                    video_info = stream
                elif stream.get('codec_type') == 'audio' and audio_info is None:
                    audio_info = stream
            
            # 動画ファイル名をベースにセットフォルダを作成
            video_name = file_path.stem
            
            # セットフォルダの作成（動画ファイル名をベースに）
            set_folder = self.final_assets_dir / video_name
            
            # 同名フォルダが存在する場合は番号を付ける
            counter = 1
            original_set_folder = set_folder
            while set_folder.exists():
                set_folder = self.final_assets_dir / f"{video_name}({counter})"
                counter += 1
            
            set_folder.mkdir(parents=True, exist_ok=True)
            self.log_callback(f"セットフォルダを作成しました: {set_folder.name}", "INFO")
            
            # 動画ファイルをセットフォルダに移動
            dest_video_path = set_folder / file_path.name
            
            # 同名ファイルが存在する場合は番号を付ける
            counter = 1
            while dest_video_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                dest_video_path = set_folder / f"{stem}({counter}){suffix}"
                counter += 1
            
            try:
                # 使用済み素材フォルダの動画かどうかをチェック
                if "使用済み素材" in file_path.parts:
                    # 使用済み素材フォルダの動画は、そのままコピーする（移動しない）
                    shutil.copy2(str(file_path), str(dest_video_path))
                    self.log_callback(f"動画ファイルをコピーしました: {dest_video_path.name} (使用済み素材フォルダから)", "INFO")
                else:
                    # 通常の動画は、使用済み素材フォルダに移動してからコピー
                    used_dir = self.lipsync_video_dir / "使用済み素材"
                    used_path = used_dir / file_path.name
                    counter = 1
                    while used_path.exists():
                        stem = file_path.stem
                        suffix = file_path.suffix
                        used_path = used_dir / f"{stem}({counter}){suffix}"
                        counter += 1
                    
                    # まず使用済み素材フォルダに移動
                    shutil.move(str(file_path), str(used_path))
                    self.log_callback(f"元ファイルを移動しました: {used_path.name}", "INFO")
                    
                    # その後、セットフォルダにコピー
                    shutil.copy2(str(used_path), str(dest_video_path))
                    self.log_callback(f"動画ファイルをコピーしました: {dest_video_path.name}", "INFO")
            except Exception as e:
                self.log_callback(f"ファイル移動に失敗しました ({file_path.name}): {str(e)}", "ERROR")
                return
            
            # XMLメタデータの生成（セットフォルダに保存）
            xml_filename = f"{video_name}_metadata.xml"
            xml_path = set_folder / xml_filename
            
            # 同名XMLが存在する場合は番号を付ける
            counter = 1
            while xml_path.exists():
                xml_filename = f"{video_name}_metadata({counter}).xml"
                xml_path = set_folder / xml_filename
                counter += 1
            
            try:
                # XMLメタデータの生成
                import xml.etree.ElementTree as ET
                from datetime import datetime
                
                root = ET.Element("MVAsset")
                root.set("version", "1.0")
                
                # 基本情報
                info = ET.SubElement(root, "Info")
                ET.SubElement(info, "FileName").text = dest_video_path.name
                ET.SubElement(info, "OriginalFileName").text = file_path.name
                ET.SubElement(info, "ProcessedDate").text = datetime.now().isoformat()
                
                # 動画情報
                if video_info:
                    video_elem = ET.SubElement(root, "Video")
                    ET.SubElement(video_elem, "Codec").text = video_info.get('codec_name', 'unknown')
                    ET.SubElement(video_elem, "Width").text = str(video_info.get('width', 0))
                    ET.SubElement(video_elem, "Height").text = str(video_info.get('height', 0))
                    ET.SubElement(video_elem, "FrameRate").text = video_info.get('r_frame_rate', 'unknown')
                    ET.SubElement(video_elem, "Duration").text = probe['format'].get('duration', '0')
                    ET.SubElement(video_elem, "Bitrate").text = str(video_info.get('bit_rate', 0))
                
                # 音声情報
                if audio_info:
                    audio_elem = ET.SubElement(root, "Audio")
                    ET.SubElement(audio_elem, "Codec").text = audio_info.get('codec_name', 'unknown')
                    ET.SubElement(audio_elem, "SampleRate").text = str(audio_info.get('sample_rate', 0))
                    ET.SubElement(audio_elem, "Channels").text = str(audio_info.get('channels', 0))
                    ET.SubElement(audio_elem, "Bitrate").text = str(audio_info.get('bit_rate', 0))
                
                # 処理履歴
                history = ET.SubElement(root, "ProcessingHistory")
                ET.SubElement(history, "QualityEnhancement").text = "Applied"
                ET.SubElement(history, "Lipsync").text = "Applied"
                ET.SubElement(history, "Finalized").text = datetime.now().isoformat()
                
                # XMLファイルに書き込み
                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ")
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
                
                self.log_callback(
                    f"XMLメタデータを生成しました: {xml_filename}",
                    "SUCCESS"
                )
                
            except Exception as e:
                self.log_callback(f"XML生成エラー ({file_path.name}): {str(e)}", "ERROR")
            
            self.log_callback(
                f"最終処理完了: {dest_video_path.name}",
                "SUCCESS"
            )
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log_callback(
                f"最終処理エラー ({file_path.name}): {str(e)}\n{error_detail}",
                "ERROR"
            )
    
    def generate_thumbnail(self, file_path: Path, timestamp: float = 1.0) -> Optional[Path]:
        """
        動画からサムネイル画像を生成
        
        Args:
            file_path: 動画ファイルのパス
            timestamp: サムネイルを抽出する時刻（秒）
        
        Returns:
            生成されたサムネイル画像のパス、またはNone
        """
        try:
            if not file_path.exists():
                return None
            
            # 一時ディレクトリにサムネイルを保存
            temp_dir = Path(tempfile.gettempdir()) / "mvai_thumbnails"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # サムネイルファイル名（ファイル名のハッシュを含めて一意にする）
            import hashlib
            file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
            thumbnail_name = f"{file_path.stem}_{file_hash}_thumb.jpg"
            thumbnail_path = temp_dir / thumbnail_name
            
            # 既に存在する場合はそれを返す
            if thumbnail_path.exists() and thumbnail_path.stat().st_size > 0:
                return thumbnail_path
            
            # 動画の長さを確認して、timestampが長さを超えないようにする
            try:
                probe = ffmpeg.probe(str(file_path))
                duration = float(probe['format'].get('duration', 0))
                if duration > 0:
                    timestamp = min(timestamp, duration - 0.5)  # 最後の0.5秒前まで
                    if timestamp < 0:
                        timestamp = 0.5  # 最小0.5秒
            except:
                timestamp = 1.0  # デフォルト値
            
            # ffmpegでサムネイルを抽出
            try:
                # 出力ファイルの拡張子が.jpgであることを確認
                if thumbnail_path.suffix.lower() != '.jpg':
                    thumbnail_path = thumbnail_path.with_suffix('.jpg')
                
                # より確実な方法でサムネイルを生成
                # subprocessを直接使用してffmpegコマンドを実行
                cmd = [
                    'ffmpeg',
                    '-ss', str(timestamp),
                    '-i', str(file_path),
                    '-vf', 'scale=320:-1',
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y',  # 上書き
                    str(thumbnail_path)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,
                    text=True
                )
                
                # 生成されたファイルを確認
                if thumbnail_path.exists():
                    file_size = thumbnail_path.stat().st_size
                    if file_size > 0:
                        return thumbnail_path
                    else:
                        # 空のファイルは削除
                        thumbnail_path.unlink()
                        return None
                else:
                    # エラーメッセージをログに記録（デバッグ用）
                    if result.stderr and self.log_callback:
                        error_msg = result.stderr[:200]
                        self.log_callback(f"サムネイル生成失敗 ({file_path.name}): {error_msg}", "ERROR")
                    return None
            except subprocess.TimeoutExpired:
                if self.log_callback:
                    self.log_callback(f"サムネイル生成タイムアウト ({file_path.name})", "ERROR")
                return None
            except FileNotFoundError:
                # ffmpegが見つからない
                if self.log_callback:
                    self.log_callback(f"FFmpegが見つかりません。FFmpegをインストールしてください。", "ERROR")
                return None
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"サムネイル生成エラー ({file_path.name}): {str(e)}", "ERROR")
                return None
            
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"サムネイル生成エラー ({file_path.name}): {str(e)}", "ERROR")
            return None
    
    def load_beat_data(self, audio_file_path: Path) -> Optional[dict]:
        """
        音声ファイルに対応するBPMとビートタイミングデータを読み込む
        
        Args:
            audio_file_path: 音声ファイルのパス
        
        Returns:
            BPMとビートタイミングの辞書、またはNone
        """
        try:
            # CSVファイル名を生成
            song_name = audio_file_path.stem
            csv_filename = f"{song_name}_beats.csv"
            csv_path = self.logs_dir / csv_filename
            
            if not csv_path.exists():
                self.log_callback(f"ビートデータが見つかりません: {csv_filename}", "WARNING")
                return None
            
            # CSVを読み込む
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            
            if 'beat_time_seconds' not in df.columns:
                self.log_callback(f"ビートデータの形式が正しくありません: {csv_filename}", "ERROR")
                return None
            
            beat_times = df['beat_time_seconds'].tolist()
            
            # BPMを計算（最初の2ビート間の時間から）
            if len(beat_times) >= 2:
                beat_interval = beat_times[1] - beat_times[0]
                bpm = 60.0 / beat_interval if beat_interval > 0 else 120.0
            else:
                bpm = 120.0  # デフォルト値
            
            return {
                'bpm': bpm,
                'beat_times': beat_times,
                'total_beats': len(beat_times)
            }
            
        except Exception as e:
            self.log_callback(f"ビートデータの読み込みエラー: {str(e)}", "ERROR")
            return None
    
    def combine_video_clips(self, video_clips: List[Path], output_path: Path, 
                           transition_duration: float = 0.5) -> bool:
        """
        複数の動画クリップを結合
        
        Args:
            video_clips: 結合する動画ファイルのパスのリスト
            output_path: 出力ファイルのパス
            transition_duration: トランジションの長さ（秒）
        
        Returns:
            成功した場合True、失敗した場合False
        """
        try:
            if not video_clips:
                self.log_callback("結合する動画クリップがありません", "ERROR")
                return False
            
            self.log_callback(f"動画クリップの結合を開始: {len(video_clips)}個のクリップ", "INFO")
            
            # 出力フォルダが存在することを確認
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 一時ファイルリストを作成（FFmpeg concat demuxer用）
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "mvai_concat"
            temp_dir.mkdir(parents=True, exist_ok=True)
            concat_file = temp_dir / "concat_list.txt"
            
            # すべてのクリップの解像度とフレームレートを統一
            target_width = 1920
            target_height = 1080
            target_fps = 24
            
            # 最初のクリップから情報を取得
            try:
                first_probe = ffmpeg.probe(str(video_clips[0]))
                first_video = next((s for s in first_probe['streams'] if s.get('codec_type') == 'video'), None)
                if first_video:
                    target_width = int(first_video.get('width', 1920))
                    target_height = int(first_video.get('height', 1080))
                    # フレームレートを取得
                    r_frame_rate = first_video.get('r_frame_rate', '24/1')
                    if '/' in r_frame_rate:
                        num, den = map(int, r_frame_rate.split('/'))
                        target_fps = num / den if den > 0 else 24
            except:
                pass
            
            # concatファイルをクリア
            if concat_file.exists():
                concat_file.unlink()
            
            # 各クリップを正規化して一時ファイルに保存
            normalized_clips = []
            for i, clip_path in enumerate(video_clips):
                try:
                    normalized_path = temp_dir / f"normalized_{i:04d}.mp4"
                    
                    # 解像度とフレームレートを統一
                    (
                        ffmpeg
                        .input(str(clip_path))
                        .filter('scale', target_width, target_height)
                        .filter('fps', target_fps)
                        .output(
                            str(normalized_path),
                            vcodec='libx264',
                            preset='fast',
                            crf=23,
                            pix_fmt='yuv420p'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    if normalized_path.exists():
                        normalized_clips.append(normalized_path)
                        # concatファイルに追加
                        with open(concat_file, 'a', encoding='utf-8') as f:
                            f.write(f"file '{normalized_path.absolute()}'\n")
                    
                except Exception as e:
                    self.log_callback(f"クリップの正規化に失敗 ({clip_path.name}): {str(e)}", "ERROR")
                    continue
            
            if not normalized_clips:
                self.log_callback("正規化されたクリップがありません", "ERROR")
                return False
            
            # FFmpeg concat demuxerで結合
            try:
                (
                    ffmpeg
                    .input(str(concat_file), format='concat', safe=0)
                    .output(
                        str(output_path),
                        vcodec='libx264',
                        preset='medium',
                        crf=23,
                        pix_fmt='yuv420p',
                        movflags='faststart'
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # 一時ファイルを削除
                for clip in normalized_clips:
                    try:
                        clip.unlink()
                    except:
                        pass
                try:
                    concat_file.unlink()
                except:
                    pass
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size = output_path.stat().st_size / (1024*1024)
                    self.log_callback(
                        f"✅ 動画クリップの結合完了: {output_path.name} ({file_size:.2f} MB)",
                        "SUCCESS"
                    )
                    return True
                else:
                    self.log_callback("結合されたファイルが生成されませんでした", "ERROR")
                    return False
                    
            except ffmpeg.Error as e:
                error_msg = ""
                if e.stderr:
                    try:
                        error_msg = e.stderr.decode('utf-8', errors='ignore')
                    except:
                        error_msg = str(e.stderr)
                self.log_callback(f"動画結合エラー: {error_msg[:300]}", "ERROR")
                return False
                
        except Exception as e:
            import traceback
            self.log_callback(f"動画結合エラー: {str(e)}\n{traceback.format_exc()[:500]}", "ERROR")
            return False
    
    def create_mv_from_clips(self, video_clips: List[Path], audio_path: Path, 
                            output_path: Path, sync_to_beat: bool = True) -> bool:
        """
        複数の動画クリップと音声からMVを生成（ビート同期対応）
        
        Args:
            video_clips: 結合する動画ファイルのパスのリスト
            audio_path: 音声ファイルのパス
            output_path: 出力ファイルのパス
            sync_to_beat: ビートに同期するかどうか
        
        Returns:
            成功した場合True、失敗した場合False
        """
        try:
            self.log_callback(f"MV生成を開始: {len(video_clips)}個のクリップ", "INFO")
            
            # 音声ファイルの存在確認
            if not audio_path.exists():
                self.log_callback(f"音声ファイルが見つかりません: {audio_path.name}", "ERROR")
                return False
            
            # 音声の長さを取得
            try:
                audio_probe = ffmpeg.probe(str(audio_path))
                audio_duration = float(audio_probe['format'].get('duration', 0))
            except:
                audio_duration = 0
            
            if audio_duration <= 0:
                self.log_callback("音声の長さを取得できませんでした", "ERROR")
                return False
            
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "mvai_mv"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # ビートデータを読み込む
            beat_data = None
            if sync_to_beat:
                beat_data = self.load_beat_data(audio_path)
                if beat_data:
                    self.log_callback(f"ビートデータを読み込みました: BPM={beat_data['bpm']:.2f}, ビート数={beat_data['total_beats']}", "INFO")
                else:
                    self.log_callback("ビートデータが見つかりません。通常の結合を行います。", "WARNING")
                    sync_to_beat = False
            
            # 各クリップの長さを取得
            clip_durations = []
            for clip in video_clips:
                try:
                    probe = ffmpeg.probe(str(clip))
                    duration = float(probe['format'].get('duration', 0))
                    clip_durations.append(duration)
                except:
                    clip_durations.append(0)
            
            # ビート同期でクリップを配置
            if sync_to_beat and beat_data:
                # ビートタイミングに合わせてクリップを配置
                beat_times = beat_data['beat_times']
                clip_segments = []
                clip_index = 0
                
                # 4ビートごとにクリップを切り替え（より自然なリズム）
                beats_per_clip = 4
                
                for i in range(0, len(beat_times), beats_per_clip):
                    if i + beats_per_clip < len(beat_times):
                        # 4ビート分の長さ
                        segment_start = beat_times[i]
                        segment_end = beat_times[i + beats_per_clip]
                        segment_duration = segment_end - segment_start
                    else:
                        # 最後の部分
                        segment_start = beat_times[i]
                        segment_end = audio_duration
                        segment_duration = segment_end - segment_start
                    
                    if segment_duration <= 0:
                        continue
                    
                    # クリップを選択（順番に使用、同じクリップが続かないように）
                    clip = video_clips[clip_index % len(video_clips)]
                    clip_duration = clip_durations[clip_index % len(video_clips)]
                    
                    if clip_duration <= 0:
                        clip_index += 1
                        continue
                    
                    # クリップをトリミング（セグメントの長さに合わせる）
                    use_duration = min(clip_duration, segment_duration)
                    
                    clip_segments.append({
                        'clip': clip,
                        'start_time': 0.0,
                        'duration': use_duration,
                        'output_start': segment_start
                    })
                    
                    # 次のクリップに切り替え（同じクリップが続かないように）
                    clip_index += 1
                
                self.log_callback(f"ビート同期: {len(clip_segments)}個のセグメントを生成（{beats_per_clip}ビートごと）", "INFO")
                
            else:
                # 通常の結合：クリップを順番に使用
                clip_segments = []
                current_time = 0.0
                clip_index = 0
                
                while current_time < audio_duration:
                    clip = video_clips[clip_index % len(video_clips)]
                    clip_duration = clip_durations[clip_index % len(video_clips)]
                    
                    remaining = audio_duration - current_time
                    use_duration = min(clip_duration, remaining)
                    
                    clip_segments.append({
                        'clip': clip,
                        'start_time': 0.0,
                        'duration': use_duration,
                        'output_start': current_time
                    })
                    
                    current_time += use_duration
                    clip_index += 1
                
                self.log_callback(f"通常結合: {len(clip_segments)}個のセグメントを生成", "INFO")
            
            # セグメントから動画を生成
            try:
                # 各セグメントを処理
                segment_files = []
                for i, segment in enumerate(clip_segments):
                    segment_file = temp_dir / f"segment_{i:04d}.mp4"
                    
                    # クリップからセグメントを抽出
                    (
                        ffmpeg
                        .input(str(segment['clip']), ss=segment['start_time'])
                        .output(
                            str(segment_file),
                            t=segment['duration'],
                            vcodec='libx264',
                            preset='fast',
                            crf=23,
                            pix_fmt='yuv420p'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    if segment_file.exists():
                        segment_files.append(segment_file)
                
                if not segment_files:
                    self.log_callback("セグメントファイルが生成されませんでした", "ERROR")
                    return False
                
                if not segment_files:
                    self.log_callback("有効なセグメントファイルがありません", "ERROR")
                    return False
                
                # セグメントを結合
                concat_file = temp_dir / "concat_list.txt"
                with open(concat_file, 'w', encoding='utf-8') as f:
                    for seg_file in segment_files:
                        f.write(f"file '{seg_file.absolute()}'\n")
                
                combined_video = temp_dir / "combined_video.mp4"
                
                # 結合された動画の長さを確認
                try:
                    (
                        ffmpeg
                        .input(str(concat_file), format='concat', safe=0)
                        .output(
                            str(combined_video),
                            vcodec='libx264',
                            preset='medium',
                            crf=23,
                            pix_fmt='yuv420p',
                            movflags='faststart'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                except ffmpeg.Error as e:
                    error_msg = ""
                    if e.stderr:
                        try:
                            error_msg = e.stderr.decode('utf-8', errors='ignore')
                        except:
                            error_msg = str(e.stderr)
                    self.log_callback(f"動画結合エラー: {error_msg[:300]}", "ERROR")
                    return False
                
                # 結合された動画の長さを確認し、音声の長さに合わせる
                try:
                    combined_probe = ffmpeg.probe(str(combined_video))
                    combined_duration = float(combined_probe['format'].get('duration', 0))
                    
                    if combined_duration < audio_duration:
                        # 動画が短い場合は、最後のセグメントを繰り返す
                        final_segment = segment_files[-1]
                        loop_count = int((audio_duration - combined_duration) / (segment_files[-1].stat().st_size / (1024*1024) * 0.1)) + 1
                        # シンプルに最後のセグメントを追加
                        with open(concat_file, 'a', encoding='utf-8') as f:
                            for _ in range(int((audio_duration - combined_duration) / 2) + 1):
                                f.write(f"file '{final_segment.absolute()}'\n")
                        
                        # 再結合
                        (
                            ffmpeg
                            .input(str(concat_file), format='concat', safe=0)
                            .output(
                                str(combined_video),
                                vcodec='libx264',
                                preset='medium',
                                crf=23,
                                pix_fmt='yuv420p',
                                movflags='faststart',
                                t=audio_duration
                            )
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    elif combined_duration > audio_duration:
                        # 動画が長い場合はトリミング
                        trimmed_video = temp_dir / "trimmed_combined.mp4"
                        (
                            ffmpeg
                            .input(str(combined_video))
                            .output(str(trimmed_video), t=audio_duration, vcodec='copy')
                            .overwrite_output()
                            .run(quiet=True)
                        )
                        combined_video = trimmed_video
                except:
                    pass
                
                # 動画と音声を結合
                video_stream = ffmpeg.input(str(combined_video))
                audio_stream = ffmpeg.input(str(audio_path))
                
                (
                    ffmpeg
                    .output(
                        video_stream,
                        audio_stream,
                        str(output_path),
                        vcodec='copy',
                        acodec='aac',
                        strict='experimental',
                        movflags='faststart'
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # 一時ファイルを削除
                try:
                    for seg_file in segment_files:
                        seg_file.unlink()
                    combined_video.unlink()
                    concat_file.unlink()
                except:
                    pass
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size = output_path.stat().st_size / (1024*1024)
                    self.log_callback(
                        f"✅ MV生成完了: {output_path.name} ({file_size:.2f} MB)",
                        "SUCCESS"
                    )
                    return True
                else:
                    self.log_callback("MVファイルが生成されませんでした", "ERROR")
                    return False
                    
            except ffmpeg.Error as e:
                error_msg = ""
                if e.stderr:
                    try:
                        error_msg = e.stderr.decode('utf-8', errors='ignore')
                    except:
                        error_msg = str(e.stderr)
                self.log_callback(f"MV生成エラー: {error_msg[:300]}", "ERROR")
                return False
                
        except Exception as e:
            import traceback
            self.log_callback(f"MV生成エラー: {str(e)}\n{traceback.format_exc()[:500]}", "ERROR")
            return False

