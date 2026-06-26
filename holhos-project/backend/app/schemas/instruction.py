from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class InstructionCreate(BaseModel):
    texto: str

class InstructionResponse(BaseModel):
    id: int
    texto: str = Field(validation_alias=AliasChoices('texto', 'text'))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
