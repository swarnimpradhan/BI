import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")

url = "https://api.monday.com/v2"

headers = {
    "Authorization": API_KEY
}

def get_board_items(board_id):

    query = f"""
    query {{
      boards(ids: {board_id}) {{
        items_page {{
          items {{
            name
            column_values {{
              text
              column {{
                title
              }}
            }}
          }}
        }}
      }}
    }}
    """

    response = requests.post(url, json={'query': query}, headers=headers)

    return response.json()