"""
nanobanana pro向けプロンプト生成
"""

from typing import Dict, List, Optional


class NanobananaPromptBuilder:
    """nanobanana pro向けプロンプトビルダー"""
    
    @staticmethod
    def build_positive_prompt(data: Dict, base_character: Optional[str] = None) -> str:
        """
        Positive Promptを構築
        
        Args:
            data: 選択されたデータ
            base_character: ベースキャラクター（I2Iの場合）
        
        Returns:
            Positive Prompt文字列
        """
        parts = []
        
        # 1. 画質と最重要要素（必ず先頭に）
        parts.append("**(masterpiece, best quality, ultra detailed)**, **absurdres**")
        
        # 2. 被写体/ポーズ
        subject_parts = []
        
        # キャラクター（base_characterは含めない）
        if data.get("character_style") and data['character_style'] != "指定なし" and data['character_style'] != "指定なし(既存のまま)":
            subject_parts.append(data['character_style'])
        
        if data.get("hair_style") and data['hair_style'] != "指定なし" and data['hair_style'] != "指定なし(既存のまま)":
            emphasis = data.get(f"hair_style_emphasis", False)
            hair_text = data['hair_style']
            if emphasis:
                subject_parts.append(f"({hair_text}:1.2)")
            else:
                subject_parts.append(hair_text)
        
        if data.get("hair_color") and data['hair_color'] != "指定なし" and data['hair_color'] != "指定なし(既存のまま)":
            emphasis = data.get(f"hair_color_emphasis", False)
            color_text = data['hair_color']
            if emphasis:
                subject_parts.append(f"({color_text} hair:1.2)")
            else:
                subject_parts.append(f"{color_text} hair")
        
        if data.get("eye_color") and data['eye_color'] != "指定なし" and data['eye_color'] != "指定なし(既存のまま)":
            emphasis = data.get(f"eye_color_emphasis", False)
            eye_text = data['eye_color']
            if emphasis:
                subject_parts.append(f"({eye_text} eyes:1.2)")
            else:
                subject_parts.append(f"{eye_text} eyes")
        
        # ポーズ
        if data.get("pose") and data['pose'] != "指定なし" and data['pose'] != "指定なし(既存のまま)":
            emphasis = data.get(f"pose_emphasis", False)
            pose_text = data['pose']
            if emphasis:
                subject_parts.append(f"({pose_text}:1.2)")
            else:
                subject_parts.append(pose_text)
        
        # 表情
        if data.get("expression") and data['expression'] != "指定なし" and data['expression'] != "指定なし(既存のまま)":
            emphasis = data.get(f"expression_emphasis", False)
            expr_text = data['expression']
            if emphasis:
                subject_parts.append(f"({expr_text}:1.2)")
            else:
                subject_parts.append(expr_text)
        
        if subject_parts:
            parts.append(", ".join(subject_parts))
        
        # 3. 服装
        outfit_parts = []
        if data.get("onepiece") and data['onepiece'] != "指定なし" and data['onepiece'] != "指定なし(既存のまま)":
            emphasis = data.get(f"onepiece_emphasis", False)
            outfit_text = data['onepiece']
            if emphasis:
                outfit_parts.append(f"({outfit_text}:1.2)")
            else:
                outfit_parts.append(outfit_text)
        else:
            if data.get("tops") and data['tops'] != "指定なし" and data['tops'] != "指定なし(既存のまま)":
                emphasis = data.get(f"tops_emphasis", False)
                tops_text = data['tops']
                if emphasis:
                    outfit_parts.append(f"({tops_text}:1.2)")
                else:
                    outfit_parts.append(tops_text)
            
            if data.get("bottoms") and data['bottoms'] != "指定なし" and data['bottoms'] != "指定なし(既存のまま)":
                emphasis = data.get(f"bottoms_emphasis", False)
                bottoms_text = data['bottoms']
                if emphasis:
                    outfit_parts.append(f"({bottoms_text}:1.2)")
                else:
                    outfit_parts.append(bottoms_text)
        
        if data.get("outerwear") and data['outerwear'] != "指定なし" and data['outerwear'] != "指定なし(既存のまま)":
            emphasis = data.get(f"outerwear_emphasis", False)
            outer_text = data['outerwear']
            if emphasis:
                outfit_parts.append(f"({outer_text}:1.2)")
            else:
                outfit_parts.append(outer_text)
        
        if data.get("socks") and data['socks'] != "指定なし" and data['socks'] != "指定なし(既存のまま)":
            emphasis = data.get(f"socks_emphasis", False)
            socks_text = data['socks']
            if emphasis:
                outfit_parts.append(f"({socks_text}:1.2)")
            else:
                outfit_parts.append(socks_text)
        
        if data.get("shoes") and data['shoes'] != "指定なし" and data['shoes'] != "指定なし(既存のまま)":
            emphasis = data.get(f"shoes_emphasis", False)
            shoes_text = data['shoes']
            if emphasis:
                outfit_parts.append(f"({shoes_text}:1.2)")
            else:
                outfit_parts.append(shoes_text)
        
        if data.get("wraps") and data['wraps'] != "指定なし" and data['wraps'] != "指定なし(既存のまま)":
            emphasis = data.get(f"wraps_emphasis", False)
            wraps_text = data['wraps']
            if emphasis:
                outfit_parts.append(f"({wraps_text}:1.2)")
            else:
                outfit_parts.append(wraps_text)
        
        if data.get("patterns"):
            if isinstance(data['patterns'], list) and data['patterns']:
                patterns_text = ", ".join([p for p in data['patterns'] if p != "指定なし" and p != "指定なし(既存のまま)"])
                if patterns_text:
                    emphasis = data.get(f"patterns_emphasis", False)
                    if emphasis:
                        outfit_parts.append(f"({patterns_text}:1.2)")
                    else:
                        outfit_parts.append(patterns_text)
        
        if outfit_parts:
            parts.append(", ".join(outfit_parts))
        
        # 4. 背景/ディテール
        detail_parts = []
        
        if data.get("background") and data['background'] != "指定なし" and data['background'] != "指定なし(既存のまま)":
            emphasis = data.get(f"background_emphasis", False)
            bg_text = data['background']
            if emphasis:
                detail_parts.append(f"({bg_text}:1.2)")
            else:
                detail_parts.append(bg_text)
        
        if data.get("lighting") and data['lighting'] != "指定なし" and data['lighting'] != "指定なし(既存のまま)":
            emphasis = data.get(f"lighting_emphasis", False)
            light_text = data['lighting']
            if emphasis:
                detail_parts.append(f"({light_text}:1.2)")
            else:
                detail_parts.append(light_text)
        
        if data.get("time_of_day") and data['time_of_day'] != "指定なし" and data['time_of_day'] != "指定なし(既存のまま)":
            emphasis = data.get(f"time_of_day_emphasis", False)
            time_text = data['time_of_day']
            if emphasis:
                detail_parts.append(f"({time_text}:1.2)")
            else:
                detail_parts.append(time_text)
        
        if data.get("mood"):
            if isinstance(data['mood'], list) and data['mood']:
                mood_text = ", ".join([m for m in data['mood'] if m != "指定なし" and m != "指定なし(既存のまま)"])
                if mood_text:
                    emphasis = data.get(f"mood_emphasis", False)
                    if emphasis:
                        detail_parts.append(f"({mood_text}:1.2)")
                    else:
                        detail_parts.append(mood_text)
        
        if detail_parts:
            parts.append(", ".join(detail_parts))
        
        # 5. その他の詳細
        if data.get("age_range") and data['age_range'] != "指定なし" and data['age_range'] != "指定なし(既存のまま)":
            parts.append(data['age_range'])
        
        if data.get("body_type") and data['body_type'] != "指定なし" and data['body_type'] != "指定なし(既存のまま)":
            parts.append(data['body_type'])
        
        if data.get("accessories"):
            if isinstance(data['accessories'], list) and data['accessories']:
                accessories_text = ", ".join([a for a in data['accessories'] if a != "指定なし" and a != "指定なし(既存のまま)"])
                if accessories_text:
                    emphasis = data.get(f"accessories_emphasis", False)
                    if emphasis:
                        parts.append(f"({accessories_text}:1.2)")
                    else:
                        parts.append(accessories_text)
        
        if data.get("additional") and data['additional'].strip():
            parts.append(data['additional'])
        
        return ", ".join(parts)
    
    @staticmethod
    def build_negative_prompt() -> str:
        """
        Negative Promptを構築（固定）
        
        Returns:
            Negative Prompt文字列
        """
        return "(worst quality, low quality:1.4), (normal quality), lowres, blurry, jpeg artifacts, watermark, logo, text, signature, username, error, monochrome, mutated hands, missing limbs, extra limbs, extra fingers, malformed limbs, long neck, bad anatomy, bad feet, out of frame, cropped"

