"""
プロンプト履歴管理モジュール
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class PromptHistory:
    """プロンプト履歴管理クラス"""
    
    MAX_HISTORY = 10
    HISTORY_FILE = "prompt_history.json"
    FAVORITES_FILE = "prompt_favorites.json"
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.history_file = base_dir / self.HISTORY_FILE
        self.favorites_file = base_dir / self.FAVORITES_FILE
    
    def add_prompt(self, prompt_type: str, positive_prompt: str, negative_prompt: str, 
                   dialog_data: Dict, final_prompt: str) -> bool:
        """
        プロンプトを履歴に追加
        
        Args:
            prompt_type: プロンプトタイプ
            positive_prompt: Positive Prompt
            negative_prompt: Negative Prompt
            dialog_data: 選択した内容のデータ
            final_prompt: 最終的なプロンプト（表示用）
        
        Returns:
            成功したかどうか
        """
        try:
            history = self.load_history()
            
            # 新しい履歴エントリを作成
            entry = {
                "id": datetime.now().isoformat(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prompt_type": prompt_type,
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "final_prompt": final_prompt,
                "dialog_data": dialog_data
            }
            
            # 先頭に追加
            history.insert(0, entry)
            
            # 最大件数を超えた場合は古いものを削除
            if len(history) > self.MAX_HISTORY:
                history = history[:self.MAX_HISTORY]
            
            return self.save_history(history)
        except Exception as e:
            print(f"プロンプト履歴の追加に失敗: {str(e)}")
            return False
    
    def load_history(self) -> List[Dict]:
        """履歴を読み込む"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def save_history(self, history: List[Dict]) -> bool:
        """履歴を保存"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"プロンプト履歴の保存に失敗: {str(e)}")
            return False
    
    def get_history(self) -> List[Dict]:
        """履歴を取得"""
        return self.load_history()
    
    def add_favorite(self, history_entry: Dict) -> bool:
        """
        お気に入りに追加
        
        Args:
            history_entry: 履歴エントリ（辞書）
        
        Returns:
            成功したかどうか
        """
        try:
            favorites = self.load_favorites()
            
            # 既に存在する場合は追加しない
            entry_id = history_entry.get("id")
            if entry_id and any(fav.get("id") == entry_id for fav in favorites):
                return False
            
            # お気に入りに追加
            favorites.append(history_entry)
            
            return self.save_favorites(favorites)
        except Exception as e:
            print(f"お気に入りの追加に失敗: {str(e)}")
            return False
    
    def load_favorites(self) -> List[Dict]:
        """お気に入りを読み込む"""
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def save_favorites(self, favorites: List[Dict]) -> bool:
        """お気に入りを保存"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"お気に入りの保存に失敗: {str(e)}")
            return False
    
    def get_favorites(self) -> List[Dict]:
        """お気に入りを取得"""
        return self.load_favorites()
    
    def remove_favorite(self, entry_id: str) -> bool:
        """お気に入りから削除"""
        try:
            favorites = self.load_favorites()
            favorites = [fav for fav in favorites if fav.get("id") != entry_id]
            return self.save_favorites(favorites)
        except Exception as e:
            print(f"お気に入りの削除に失敗: {str(e)}")
            return False

