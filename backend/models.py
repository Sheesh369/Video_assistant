from pydantic import BaseModel, Field, field_validator
from typing import Literal

class PromptRequest(BaseModel):
    """Request model for sending prompts to the avatar"""
    prompt: str = Field(..., min_length=1, description="The text prompt to send to the avatar")

class CreateSessionRequest(BaseModel):
    """Request model for creating a new HeyGen session with specific avatar and voice"""
    avatar_id: str = Field(
        ..., 
        description="The unique identifier for the HeyGen avatar",
        example="josh_lite3_20230714"
    )
    voice_id: str = Field(
        ..., 
        description="The unique identifier for the voice to use with the avatar",
        example="da04d9a268ac468887a68359908e55b7"
    )
    
    @field_validator('avatar_id', 'voice_id')
    @classmethod
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "avatar_id": "josh_lite3_20230714",
                    "voice_id": "da04d9a268ac468887a68359908e55b7",
                    "description": "Male - Josh (Professional)"
                },
                {
                    "avatar_id": "Anthony_Chair_Sitting_public",
                    "voice_id": "0009aabefe3a4553bc581d837b6268cb",
                    "description": "Male - Anthony (Corporate)"
                },
                {
                    "avatar_id": "Pedro_Chair_Sitting_public",
                    "voice_id": "e17b99e1b86e47e8b7f4cae0f806aa78",
                    "description": "Male - Pedro (Technical)"
                },
                {
                    "avatar_id": "Alessandra_Chair_Sitting_public",
                    "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
                    "description": "Female - Alessandra (Executive)"
                },
                {
                    "avatar_id": "Amina_Chair_Sitting_public",
                    "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
                    "description": "Female - Amina (Advisory)"
                },
                {
                    "avatar_id": "Anastasia_Chair_Sitting_public",
                    "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
                    "description": "Female - Anastasia (Operations)"
                },
                {
                    "avatar_id": "Marianne_Chair_Sitting_public",
                    "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
                    "description": "Female - Marianne (Senior Advisor)"
                },
                {
                    "avatar_id": "Rika_Chair_Sitting_public",
                    "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
                    "description": "Female - Rika (Specialist)"
                }
            ]
        }
    }


# Avatar configuration constants for easy reference
AVATAR_CONFIGS = {
    # Male avatars
    "josh": {
        "id": "josh_lite3_20230714",
        "voice_id": "da04d9a268ac468887a68359908e55b7",
        "name": "Josh",
        "gender": "male",
        "description": "Professional executive consultant"
    },
    "anthony": {
        "id": "Anthony_Chair_Sitting_public",
        "voice_id": "0009aabefe3a4553bc581d837b6268cb",
        "name": "Anthony",
        "gender": "male",
        "description": "Corporate senior advisor"
    },
    "pedro": {
        "id": "Pedro_Chair_Sitting_public",
        "voice_id": "e17b99e1b86e47e8b7f4cae0f806aa78",
        "name": "Pedro",
        "gender": "male",
        "description": "Technical solutions architect"
    },
    # Female avatars
    "alessandra": {
        "id": "Alessandra_Chair_Sitting_public",
        "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
        "name": "Alessandra",
        "gender": "female",
        "description": "Executive business strategist"
    },
    "amina": {
        "id": "Amina_Chair_Sitting_public",
        "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
        "name": "Amina",
        "gender": "female",
        "description": "Client relations specialist"
    },
    "anastasia": {
        "id": "Anastasia_Chair_Sitting_public",
        "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
        "name": "Anastasia",
        "gender": "female",
        "description": "Operations and process expert"
    },
    "marianne": {
        "id": "Marianne_Chair_Sitting_public",
        "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
        "name": "Marianne",
        "gender": "female",
        "description": "Senior industry advisor"
    },
    "rika": {
        "id": "Rika_Chair_Sitting_public",
        "voice_id": "1edc5e7338eb4e37b26dc8eb3f9b7e9c",
        "name": "Rika",
        "gender": "female",
        "description": "Domain specialist consultant"
    }
}

# Helper function to get all avatar options
def get_all_avatars():
    """Returns a list of all available avatar configurations"""
    return [
        {
            "id": config["id"],
            "voice_id": config["voice_id"],
            "name": config["name"],
            "gender": config["gender"],
            "description": config["description"]
        }
        for config in AVATAR_CONFIGS.values()
    ]

# Helper function to get avatars by gender
def get_avatars_by_gender(gender: Literal["male", "female"]):
    """Returns avatars filtered by gender"""
    return [
        {
            "id": config["id"],
            "voice_id": config["voice_id"],
            "name": config["name"],
            "gender": config["gender"],
            "description": config["description"]
        }
        for config in AVATAR_CONFIGS.values()
        if config["gender"] == gender
    ]