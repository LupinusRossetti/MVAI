"""
Gemini APIを使用したプロンプト生成アシスタント
"""

import os
import google.generativeai as genai
from typing import Optional


class PromptGenerator:
    """プロンプト生成クラス"""
    
    SYSTEM_PROMPT = """あなたはルピナス、アイリス、フィオナの三姉妹によるMV制作用のプロンプト作成専門家です。監督の指示を、カメラワーク、照明、テクスチャを含む、最高品質の動画生成AI（Sora, Grok, Luma等）が理解できる具体的で技術的な英語プロンプトに変換してください。回答は英語のみとし、不要な解説は一切含めないでください。"""
    
    def __init__(self):
        """初期化"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        
        genai.configure(api_key=api_key)
        
        # 利用可能なモデルを動的に確認
        try:
            # 利用可能なモデル一覧を取得
            models = genai.list_models()
            available_models = []
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    # モデル名から "models/" プレフィックスを除去
                    model_name = m.name.replace('models/', '')
                    available_models.append(model_name)
            
            # 優先順位でモデルを選択
            model_priority = [
                'gemini-1.5-flash-latest',
                'gemini-1.5-pro-latest',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-pro'
            ]
            
            selected_model = None
            for model_name in model_priority:
                if model_name in available_models:
                    selected_model = model_name
                    break
            
            if selected_model:
                self.model = genai.GenerativeModel(selected_model)
            else:
                # フォールバック: 最初に見つかったモデルを使用
                if available_models:
                    self.model = genai.GenerativeModel(available_models[0])
                else:
                    raise Exception("利用可能なモデルが見つかりません")
        except Exception as e:
            # エラー時はgemini-proを試す
            try:
                self.model = genai.GenerativeModel('gemini-pro')
            except:
                raise Exception(f"モデルの初期化に失敗しました: {str(e)}")
    
    def _generate_prompt(self, user_input: str, context: str = "") -> str:
        """
        プロンプトを生成する内部メソッド
        
        Args:
            user_input: ユーザーの入力
            context: 追加のコンテキスト情報
        
        Returns:
            生成されたプロンプト（英語）
        """
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{context}\n\n監督の指示: {user_input}\n\nプロンプト:"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Gemini API呼び出しエラー: {str(e)}")
    
    def generate_suno_prompt(self, user_input: str) -> str:
        """
        Suno AI用のプロンプトを生成
        
        Args:
            user_input: 監督の指示
        
        Returns:
            Suno用のプロンプト
        """
        context = "以下の指示をSuno AIで音楽生成するためのプロンプトに変換してください。"
        return self._generate_prompt(user_input, context)
    
    def generate_sora_grok_prompt(self, user_input: str) -> str:
        """
        Sora/Grok用のベースプロンプトを生成
        
        Args:
            user_input: 監督の指示
        
        Returns:
            Sora/Grok用のプロンプト
        """
        context = """以下の指示をSoraやGrokなどの動画生成AI用のプロンプトに変換してください。
カメラワーク（カメラの動き、アングル、ズーム）、照明（光の方向、強さ、色）、
テクスチャ、被写体の動き、背景などを具体的に記述してください。"""
        return self._generate_prompt(user_input, context)
    
    def generate_grok_scene_prompt(self, user_input: str) -> str:
        """
        Grok Scene用のプロンプトを生成
        
        Args:
            user_input: 監督の指示
        
        Returns:
            Grok Scene用のプロンプト
        """
        context = """以下の指示をGrok Scene用のシーンプロンプトに変換してください。
シーンの構成、キャラクターの配置、動き、感情表現、環境の詳細を
技術的で具体的な英語で記述してください。"""
        return self._generate_prompt(user_input, context)

