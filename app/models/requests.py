from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=["What are the main findings of this document?"],
    )
    top_k: int = Field(default=5, ge=1, le=20)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What are the main findings of this document?",
                    "top_k": 5,
                    "temperature": 0.2,
                }
            ]
        }
    }
