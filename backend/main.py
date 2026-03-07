import os
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel

from fastapi import FastAPI, File, HTTPException, UploadFile
from dotenv import load_dotenv

load_dotenv()


client = genai.Client(api_key=os.environ["GEMINI_SECRET"])
app = FastAPI()


class GroceryItem(BaseModel):
    name: str
    price: float | None
    quantity: float | None
    query: str


class GroceryList(BaseModel):
    items: List[GroceryItem]


@app.post("/scan")
async def scan_grocery_image(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await image.read()

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            types.Part.from_bytes(data=contents, mime_type=image.content_type),
            "List all the grocery items visible in this image, including their price and quantity if shown. For each item also provide a query field: the simplest generic 1-2 word search term for that item (e.g. 'Natrel 3.25% Milk 4L' → 'milk', 'Wonder White Sandwich Bread' → 'bread').",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GroceryList,
        ),
    )

    items = [item.model_dump() for item in response.parsed.items]


    return {"items": items}

