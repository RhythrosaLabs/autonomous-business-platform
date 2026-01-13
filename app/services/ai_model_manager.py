"""
AI Model Management System
Handles model selection, fallback, quality assessment, and optimization
"""

import logging
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoModel(Enum):
    """Available video generation models."""
    SORA = "sora"
    KLING = "kling"
    KEN_BURNS = "ken_burns"
    MINIMAX = "minimax"
    LUMA = "luma"


class ModelPriority:
    """Model priority and fallback configuration."""
    
    QUALITY_TIERS = {
        "premium": [VideoModel.SORA, VideoModel.KLING, VideoModel.LUMA, VideoModel.KEN_BURNS],
        "standard": [VideoModel.KLING, VideoModel.LUMA, VideoModel.KEN_BURNS],
        "fast": [VideoModel.KEN_BURNS, VideoModel.KLING],
        "free": [VideoModel.KEN_BURNS]
    }
    
    MODEL_CAPABILITIES = {
        VideoModel.SORA: {
            "name": "Sora-2 (OpenAI)",
            "quality": 95,
            "speed": 30,
            "cost": 90,
            "features": ["cinematic", "audio", "realistic_motion", "complex_scenes"],
            "max_duration": 12,
            "strengths": "Best for cinematic quality, realistic physics, professional production",
            "weaknesses": "Slower, more expensive, may have availability issues"
        },
        VideoModel.KLING: {
            "name": "Kling AI",
            "quality": 90,
            "speed": 50,
            "cost": 70,
            "features": ["animated", "creative_effects", "smooth_transitions", "stylized"],
            "max_duration": 10,
            "strengths": "Great for creative animations, smooth motion, reliable",
            "weaknesses": "Less photorealistic than Sora, stylized look"
        },
        VideoModel.KEN_BURNS: {
            "name": "Ken Burns Effect",
            "quality": 75,
            "speed": 95,
            "cost": 5,
            "features": ["fast", "reliable", "customizable", "local_processing"],
            "max_duration": 60,
            "strengths": "Instant generation, no API costs, unlimited duration, always available",
            "weaknesses": "Limited to zoom/pan effects, requires good source images"
        },
        VideoModel.LUMA: {
            "name": "Luma AI",
            "quality": 85,
            "speed": 60,
            "cost": 60,
            "features": ["fast", "reliable", "good_motion", "consistent"],
            "max_duration": 10,
            "strengths": "Fast generation, consistent quality, good reliability",
            "weaknesses": "Less cinematic than Sora, fewer creative options than Kling"
        }
    }


class QualityAssessor:
    """Assess video/image quality before saving."""
    
    @staticmethod
    def assess_video_quality(video_path: str) -> Dict[str, Any]:
        """
        Assess video quality using multiple metrics.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with quality scores and assessment
        """
        try:
            from moviepy.editor import VideoFileClip
            import cv2
            import numpy as np
            
            scores = {
                "overall": 0,
                "resolution": 0,
                "duration": 0,
                "frame_rate": 0,
                "sharpness": 0,
                "brightness": 0,
                "assessment": "unknown",
                "issues": [],
                "passed": False
            }
            
            # Basic file checks
            if not Path(video_path).exists():
                scores["assessment"] = "file_not_found"
                scores["issues"].append("Video file does not exist")
                return scores
            
            file_size = Path(video_path).stat().st_size
            if file_size < 1000:  # Less than 1KB
                scores["assessment"] = "corrupted"
                scores["issues"].append("File size too small, likely corrupted")
                return scores
            
            # Load video
            clip = VideoFileClip(video_path)
            
            # Check duration
            if clip.duration < 1:
                scores["issues"].append("Video too short (< 1 second)")
                scores["duration"] = 20
            elif clip.duration >= 3:
                scores["duration"] = 100
            else:
                scores["duration"] = 60
            
            # Check resolution
            width, height = clip.size
            resolution_score = min(100, (width * height) / (1920 * 1080) * 100)
            scores["resolution"] = resolution_score
            
            if width < 720 or height < 480:
                scores["issues"].append(f"Low resolution: {width}x{height}")
            
            # Check frame rate
            fps = clip.fps
            if fps < 20:
                scores["issues"].append(f"Low frame rate: {fps}fps")
                scores["frame_rate"] = 50
            elif fps >= 24:
                scores["frame_rate"] = 100
            else:
                scores["frame_rate"] = 75
            
            # Sample frames for quality analysis
            try:
                mid_frame = clip.get_frame(clip.duration / 2)
                
                # Convert to grayscale for analysis
                gray = cv2.cvtColor(mid_frame, cv2.COLOR_RGB2GRAY)
                
                # Check sharpness (Laplacian variance)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                if laplacian_var < 50:
                    scores["issues"].append("Video appears blurry")
                    scores["sharpness"] = 40
                elif laplacian_var > 500:
                    scores["sharpness"] = 100
                else:
                    scores["sharpness"] = min(100, (laplacian_var / 500) * 100)
                
                # Check brightness
                mean_brightness = np.mean(mid_frame)
                if mean_brightness < 50:
                    scores["issues"].append("Video too dark")
                    scores["brightness"] = 50
                elif mean_brightness > 200:
                    scores["issues"].append("Video too bright/overexposed")
                    scores["brightness"] = 60
                else:
                    scores["brightness"] = 100
                    
            except Exception as frame_error:
                logger.warning(f"Frame analysis failed: {frame_error}")
                scores["sharpness"] = 70  # Assume acceptable
                scores["brightness"] = 70
            
            clip.close()
            
            # Calculate overall score
            weights = {
                "resolution": 0.25,
                "duration": 0.15,
                "frame_rate": 0.20,
                "sharpness": 0.25,
                "brightness": 0.15
            }
            
            overall = sum(scores[key] * weight for key, weight in weights.items())
            scores["overall"] = round(overall, 1)
            
            # Determine assessment
            if overall >= 80:
                scores["assessment"] = "excellent"
                scores["passed"] = True
            elif overall >= 65:
                scores["assessment"] = "good"
                scores["passed"] = True
            elif overall >= 50:
                scores["assessment"] = "acceptable"
                scores["passed"] = True
            else:
                scores["assessment"] = "poor"
                scores["passed"] = False
            
            return scores
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {
                "overall": 50,
                "assessment": "error",
                "issues": [f"Assessment failed: {str(e)}"],
                "passed": True  # Pass by default to avoid blocking
            }
    
    @staticmethod
    def should_regenerate(quality_scores: Dict, threshold: float = 65.0) -> bool:
        """Determine if video should be regenerated based on quality."""
        return not quality_scores.get("passed", True) or quality_scores.get("overall", 100) < threshold


class ModelFallbackManager:
    """Manage model fallback and retry logic."""
    
    def __init__(self, quality_tier: str = "standard"):
        self.quality_tier = quality_tier
        self.priority_list = ModelPriority.QUALITY_TIERS.get(quality_tier, ModelPriority.QUALITY_TIERS["standard"])
        self.attempt_log = []
    
    def generate_with_fallback(
        self,
        generation_func: Callable,
        model_order: Optional[List[VideoModel]] = None,
        max_attempts_per_model: int = 2,
        quality_threshold: float = 65.0,
        **kwargs
    ) -> Tuple[Optional[str], Dict]:
        """
        Try to generate video with automatic model fallback.
        
        Args:
            generation_func: Function that takes model and kwargs, returns video path
            model_order: Custom model priority order (uses tier default if None)
            max_attempts_per_model: Retry attempts per model
            quality_threshold: Minimum quality score to accept
            **kwargs: Arguments passed to generation function
            
        Returns:
            Tuple of (video_path, metadata)
        """
        if model_order is None:
            model_order = self.priority_list
        
        assessor = QualityAssessor()
        
        for model in model_order:
            model_info = ModelPriority.MODEL_CAPABILITIES[model]
            logger.info(f"🎬 Trying {model_info['name']}...")
            
            for attempt in range(max_attempts_per_model):
                try:
                    start_time = time.time()
                    
                    # Generate video
                    video_path = generation_func(model=model, **kwargs)
                    
                    generation_time = time.time() - start_time
                    
                    if not video_path or not Path(video_path).exists():
                        logger.warning(f"⚠️ {model_info['name']} attempt {attempt+1}: No output produced")
                        continue
                    
                    # Assess quality
                    quality = assessor.assess_video_quality(video_path)
                    
                    self.attempt_log.append({
                        "model": model.value,
                        "attempt": attempt + 1,
                        "success": True,
                        "quality_score": quality["overall"],
                        "generation_time": generation_time,
                        "issues": quality["issues"]
                    })
                    
                    # Check if quality is acceptable
                    if quality["overall"] >= quality_threshold:
                        logger.info(f"✅ {model_info['name']}: Quality score {quality['overall']}/100 - ACCEPTED")
                        
                        metadata = {
                            "model": model.value,
                            "model_name": model_info["name"],
                            "attempt": attempt + 1,
                            "quality_score": quality["overall"],
                            "quality_assessment": quality["assessment"],
                            "generation_time": generation_time,
                            "fallback_attempts": len(self.attempt_log)
                        }
                        
                        return video_path, metadata
                    else:
                        logger.warning(
                            f"⚠️ {model_info['name']}: Quality score {quality['overall']}/100 - "
                            f"BELOW THRESHOLD ({quality_threshold})"
                        )
                        if attempt < max_attempts_per_model - 1:
                            logger.info(f"🔄 Retrying {model_info['name']}...")
                        
                except Exception as e:
                    logger.error(f"❌ {model_info['name']} attempt {attempt+1} failed: {e}")
                    
                    self.attempt_log.append({
                        "model": model.value,
                        "attempt": attempt + 1,
                        "success": False,
                        "error": str(e)
                    })
                    
                    if attempt < max_attempts_per_model - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
            
            # This model exhausted, try next in fallback chain
            logger.warning(f"⚠️ {model_info['name']} exhausted, trying fallback model...")
        
        # All models failed
        logger.error("❌ All models failed to produce acceptable video")
        
        return None, {
            "model": "none",
            "success": False,
            "attempts": self.attempt_log,
            "message": "All video generation models failed"
        }
    
    def get_recommended_model(
        self,
        requirements: Dict[str, Any]
    ) -> VideoModel:
        """
        Recommend best model based on requirements.
        
        Args:
            requirements: Dict with keys like duration, quality_needed, budget, speed_priority
            
        Returns:
            Recommended VideoModel
        """
        duration = requirements.get("duration", 10)
        quality_needed = requirements.get("quality_needed", "high")
        budget = requirements.get("budget", "medium")
        speed_priority = requirements.get("speed_priority", False)
        
        # Speed priority
        if speed_priority:
            return VideoModel.KEN_BURNS
        
        # Budget constraints
        if budget == "low" or budget == "free":
            return VideoModel.KEN_BURNS
        
        # Duration constraints
        if duration > 12:
            return VideoModel.KEN_BURNS
        
        # Quality requirements
        if quality_needed == "ultra" or quality_needed == "cinematic":
            return VideoModel.SORA
        elif quality_needed == "creative" or quality_needed == "animated":
            return VideoModel.KLING
        elif quality_needed == "fast":
            return VideoModel.KEN_BURNS
        
        # Default to balanced choice
        return VideoModel.KLING


if __name__ == "__main__":
    print("🎬 AI Model Management System Demo\n")
    
    print("="*60)
    print("Available Video Models:")
    print("="*60)
    for model in VideoModel:
        info = ModelPriority.MODEL_CAPABILITIES[model]
        print(f"\n{info['name']}")
        print(f"  Quality: {info['quality']}/100")
        print(f"  Speed: {info['speed']}/100")
        print(f"  Cost: {info['cost']}/100")
        print(f"  Max Duration: {info['max_duration']}s")
        print(f"  Strengths: {info['strengths']}")
    
    print("\n" + "="*60)
    print("Model Recommendation Examples:")
    print("="*60)
    
    manager = ModelFallbackManager()
    
    scenarios = [
        {"duration": 5, "quality_needed": "cinematic", "budget": "high", "speed_priority": False},
        {"duration": 10, "quality_needed": "good", "budget": "medium", "speed_priority": False},
        {"duration": 30, "quality_needed": "acceptable", "budget": "low", "speed_priority": True},
    ]
    
    for i, req in enumerate(scenarios, 1):
        recommended = manager.get_recommended_model(req)
        print(f"\nScenario {i}: {req}")
        print(f"  Recommended: {ModelPriority.MODEL_CAPABILITIES[recommended]['name']}")
