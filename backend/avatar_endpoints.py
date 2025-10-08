"""
Additional FastAPI endpoints for avatar management
Add these to your main FastAPI application
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from models import (
    get_all_avatars, 
    get_free_avatars,
    get_avatars_by_gender, 
    get_avatar_by_id,
    get_avatar_by_name,
    validate_avatar_voice_pair,
    AVATAR_CONFIGS,
    FREE_AVATAR_CONFIGS
)

router = APIRouter(prefix="/api/avatars", tags=["avatars"])


@router.get("/list", response_model=List[Dict])
async def list_all_avatars():
    """
    Get a list of all available avatars with their configurations
    
    Returns:
        List of avatar configurations including id, voice_id, name, gender, and description
    """
    return get_all_avatars()


@router.get("/free", response_model=List[Dict])
async def list_free_avatars():
    """
    Get a list of free HeyGen avatars with their configurations
    
    Returns:
        List of free avatar configurations
    """
    return get_free_avatars()


@router.get("/list/{gender}", response_model=List[Dict])
async def list_avatars_by_gender(gender: str):
    """
    Get avatars filtered by gender
    
    Args:
        gender: Either 'male' or 'female'
    
    Returns:
        List of filtered avatar configurations
    """
    if gender.lower() not in ["male", "female"]:
        raise HTTPException(
            status_code=400, 
            detail="Gender must be either 'male' or 'female'"
        )
    
    return get_avatars_by_gender(gender.lower())


@router.get("/details/{avatar_name}", response_model=Dict)
async def get_avatar_details(avatar_name: str):
    """
    Get detailed information about a specific avatar by name
    
    Args:
        avatar_name: The name key of the avatar (e.g., 'josh', 'alessandra')
    
    Returns:
        Avatar configuration details
    """
    avatar_name_lower = avatar_name.lower()
    
    if avatar_name_lower not in AVATAR_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"Avatar '{avatar_name}' not found. Available avatars: {', '.join(AVATAR_CONFIGS.keys())}"
        )
    
    return AVATAR_CONFIGS[avatar_name_lower]


@router.get("/by-id/{avatar_id}", response_model=Dict)
async def get_avatar_by_id_endpoint(avatar_id: str):
    """
    Get avatar configuration by HeyGen avatar ID
    
    Args:
        avatar_id: The HeyGen avatar ID (e.g., 'josh_lite3_20230714')
    
    Returns:
        Avatar configuration details
    """
    avatar = get_avatar_by_id(avatar_id)
    
    if not avatar:
        raise HTTPException(
            status_code=404,
            detail=f"Avatar with ID '{avatar_id}' not found"
        )
    
    return avatar


@router.get("/validate")
async def validate_avatar_voice_pair_endpoint(avatar_id: str, voice_id: str):
    """
    Validate if an avatar_id and voice_id pair exists in the configuration
    
    Args:
        avatar_id: The HeyGen avatar ID
        voice_id: The HeyGen voice ID
    
    Returns:
        Validation result with avatar details if found
    """
    return validate_avatar_voice_pair(avatar_id, voice_id)


@router.get("/stats")
async def get_avatar_stats():
    """
    Get statistics about available avatars
    
    Returns:
        Statistics including total count and gender distribution
    """
    all_avatars = get_all_avatars()
    free_avatars = get_free_avatars()
    
    male_count = len([a for a in all_avatars if a["gender"] == "male"])
    female_count = len([a for a in all_avatars if a["gender"] == "female"])
    
    free_male_count = len([a for a in free_avatars if a["gender"] == "male"])
    free_female_count = len([a for a in free_avatars if a["gender"] == "female"])
    
    # Count unique voice IDs
    unique_voices = len(set(a["voice_id"] for a in all_avatars))
    unique_free_voices = len(set(a["voice_id"] for a in free_avatars))
    
    return {
        "total_avatars": len(all_avatars),
        "free_avatars": len(free_avatars),
        "male_avatars": male_count,
        "female_avatars": female_count,
        "free_male_avatars": free_male_count,
        "free_female_avatars": free_female_count,
        "unique_voices": unique_voices,
        "unique_free_voices": unique_free_voices,
        "avatars_by_name": list(AVATAR_CONFIGS.keys()),
        "free_avatars_by_name": list(FREE_AVATAR_CONFIGS.keys())
    }


@router.get("/categories")
async def get_avatar_categories():
    """
    Get all available avatar categories
    
    Returns:
        List of unique categories with avatar counts
    """
    categories = {}
    for avatar in get_all_avatars():
        category = avatar.get("category", "uncategorized")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    return {
        "categories": categories,
        "total_categories": len(categories)
    }


@router.get("/recommended")
async def get_recommended_avatars():
    """
    Get recommended free avatars for different use cases
    
    Returns:
        Recommended avatars organized by use case
    """
    return {
        "business": [
            avatar for avatar in get_free_avatars() 
            if avatar["category"] in ["business", "executive", "corporate"]
        ],
        "technical": [
            avatar for avatar in get_free_avatars() 
            if avatar["category"] in ["technical", "specialist"]
        ],
        "advisory": [
            avatar for avatar in get_free_avatars() 
            if avatar["category"] in ["advisory", "senior", "operations"]
        ],
        "all_free": get_free_avatars()
    }
