"""
キャラクター画像管理モジュール
"""

from pathlib import Path
import shutil
import json
from typing import List, Dict, Optional


class CharacterManager:
    """キャラクター画像管理クラス"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.characters_dir = base_dir / "00_キャラクター"
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.characters_dir / ".characters.json"
    
    def load_characters(self) -> Dict[str, Dict]:
        """登録されているキャラクター一覧を読み込む"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_characters(self, characters: Dict[str, Dict]):
        """キャラクター情報を保存"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(characters, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"キャラクター情報の保存に失敗: {str(e)}")
            return False
    
    def add_character(self, name: str, image_path: Path, uploaded_file=None) -> Optional[Path]:
        """
        新しいキャラクター画像を追加（同名の場合は同じフォルダに保存）
        
        Args:
            name: キャラクター名
            image_path: 画像ファイルのパス（一時ファイルの場合）
            uploaded_file: StreamlitのUploadedFileオブジェクト（優先）
        
        Returns:
            保存された画像のパス、またはNone
        """
        if not name.strip():
            return None
        
        # フォルダ名として使用可能な文字に変換
        folder_name = name.strip()
        
        # 既存のキャラクター情報を読み込む
        characters = self.load_characters()
        
        # キャラクター専用フォルダを作成（既存の場合はそのまま使用）
        char_dir = self.characters_dir / folder_name
        char_dir.mkdir(parents=True, exist_ok=True)
        
        # 画像ファイル名を決定
        if uploaded_file:
            original_filename = Path(uploaded_file.name).stem
            image_ext = Path(uploaded_file.name).suffix
        else:
            original_filename = image_path.stem
            image_ext = image_path.suffix
        
        # 同じファイル名が存在する場合は番号を付ける
        dest_filename = f"{original_filename}{image_ext}"
        dest_image_path = char_dir / dest_filename
        counter = 1
        while dest_image_path.exists():
            dest_filename = f"{original_filename}({counter}){image_ext}"
            dest_image_path = char_dir / dest_filename
            counter += 1
        
        try:
            # 画像を保存
            if uploaded_file:
                with open(dest_image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            else:
                shutil.copy2(image_path, dest_image_path)
            
            # メタデータを更新（既存のキャラクターの場合は画像リストを更新）
            if folder_name not in characters:
                characters[folder_name] = {
                    "name": name,
                    "folder_name": folder_name,
                    "images": [],
                    "created_at": str(Path(dest_image_path).stat().st_mtime),
                    "attributes": {}
                }
            
            # 画像パスをリストに追加
            image_relative_path = str(dest_image_path.relative_to(self.base_dir))
            if image_relative_path not in characters[folder_name].get("images", []):
                if "images" not in characters[folder_name]:
                    characters[folder_name]["images"] = []
                characters[folder_name]["images"].append(image_relative_path)
            
            # 最初の画像をメイン画像として設定（まだ設定されていない場合）
            if "image_path" not in characters[folder_name] or not characters[folder_name]["image_path"]:
                characters[folder_name]["image_path"] = image_relative_path
            
            self.save_characters(characters)
            return dest_image_path
        except Exception as e:
            print(f"キャラクター追加エラー: {str(e)}")
            return None
    
    def get_character_list(self) -> List[str]:
        """登録されているキャラクター名のリストを取得"""
        characters = self.load_characters()
        return [char_info["name"] for char_info in characters.values()]
    
    def get_character_folders(self) -> List[str]:
        """キャラクターのフォルダ名リストを取得"""
        characters = self.load_characters()
        return list(characters.keys())
    
    def delete_character(self, folder_name: str) -> bool:
        """キャラクターを削除"""
        characters = self.load_characters()
        
        if folder_name in characters:
            # フォルダを削除
            char_dir = self.characters_dir / folder_name
            if char_dir.exists():
                try:
                    shutil.rmtree(char_dir)
                except Exception as e:
                    print(f"フォルダ削除エラー: {str(e)}")
            
            # メタデータから削除
            del characters[folder_name]
            return self.save_characters(characters)
        
        return False
    
    def get_character_attributes(self, character_name: str) -> Dict:
        """キャラクターの属性を取得"""
        characters = self.load_characters()
        for folder_name, char_info in characters.items():
            if char_info.get("name") == character_name:
                return char_info.get("attributes", {})
        return {}
    
    def save_character_attributes(self, character_name: str, attributes: Dict) -> bool:
        """キャラクターの属性を保存"""
        characters = self.load_characters()
        for folder_name, char_info in characters.items():
            if char_info.get("name") == character_name:
                char_info["attributes"] = attributes
                return self.save_characters(characters)
        return False
    
    def get_character_images(self, character_name: str) -> List[Path]:
        """キャラクターのフォルダ内の全画像を取得"""
        characters = self.load_characters()
        for folder_name, char_info in characters.items():
            if char_info.get("name") == character_name:
                char_dir = self.characters_dir / folder_name
                if char_dir.exists():
                    # 画像ファイルのみを取得
                    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
                    images = []
                    for img_path in char_dir.iterdir():
                        if img_path.is_file() and img_path.suffix.lower() in image_extensions:
                            images.append(img_path)
                    return sorted(images)
        return []
    
    def get_character_folder_path(self, character_name: str) -> Optional[Path]:
        """キャラクターのフォルダパスを取得"""
        characters = self.load_characters()
        for folder_name, char_info in characters.items():
            if char_info.get("name") == character_name:
                return self.characters_dir / folder_name
        return None

