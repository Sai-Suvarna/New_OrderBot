from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    HTTPException,
    status,
    Cookie,
)
from fastapi.routing import APIRouter
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from chat1 import collect_messages_text1,payment
from chat2 import get_completion_from_messages2,collect_messages_text2
from chat3 import get_completion_from_messages3,collect_messages_text3
from chat4 import get_completion_from_messages4,collect_messages_text4
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from fastapi.responses import JSONResponse,HTMLResponse
import random
import os,uuid
import json
import logging
from google.cloud import bigquery
from fastapi.responses import HTMLResponse
from fastapi import Request

# Set your Google Cloud project ID
project_id = 'ck-eams'

# Initialize a BigQuery client
client = bigquery.Client(project=project_id)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (use logging.DEBUG for more detailed logs)
    filename="app.log",  # Specify a file to write logs (optional)
    format="%(asctime)s [%(levelname)s]: %(message)s",  # Define log format
)

# Initialize FastAPI app
app = FastAPI()
router = APIRouter()

# Create an instance of HTTPBasic for security
security = HTTPBasic()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

# User Database (for demonstration purposes)
users = {}

# In-memory session storage (for demonstration purposes)
sessions = {}


class SessionData(BaseModel):
    username: str


class Message(BaseModel):
    content: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request, error: str = None):
    return templates.TemplateResponse(
        "index1.html", {"request": request, "error": error}
    )
@app.post("/logout", response_class=RedirectResponse)
def logout(session_id: str = Cookie(None, alias="session_id")):
    if session_id is not None and session_id in sessions:
        sessions.pop(session_id)

    # Delete tableNumber cookie (assuming it's also set on the client)
    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
        headers={
            "Set-Cookie": f"sessionId=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; Secure; SameSite=Lax",
            "Set-Cookie": f"tableNumber=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; Secure; SameSite=Lax",
        },
    )


@app.post("/chat1", response_model=dict)
async def chat1(
    request: Request, 
    message: Message
):
    user_message = message.content

    if not user_message:
        return {"message": "Received an empty message."}

    try:
        session_id = request.cookies.get("sessionId")
        table_number = request.cookies.get("tableNumber")
        response = collect_messages_text1(user_message, session_id, table_number)  # Pass session_id as a parameter
        print(session_id)
        return {"message": response}
    except Exception as e:
        print(f"Error in chat1: {e}")
        return {"message": "An error occurred."}



@app.post("/process_voice", response_model=dict)
async def process_voice(request: Request,voice_input: dict):
    text = voice_input.get("input")
    session_id = request.cookies.get("sessionId")
    response = collect_messages_text1(text,session_id)
    return {"message": response}



@app.get("/templates/index1.html")
def index1(request: Request):
    return templates.TemplateResponse("index1.html", {"request": request})


# @app.get("/hotel1", response_class=HTMLResponse)
# async def hotel1(request: Request):
#     return templates.TemplateResponse("hotel1.html", {"request": request})

@app.get("/hotel1.html", response_class=HTMLResponse)
def hotel1(request: Request):
    return templates.TemplateResponse("hotel1.html", {"request": request})

@app.get("/payment.html", response_class=HTMLResponse)
def payment(request: Request):
    return templates.TemplateResponse("payment.html", {"request": request})


@app.get("/index1.html", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index1.html", {"request": request})


@app.get("/get_order_summary", response_model=list[dict])
def get_order_summary_from_db(session_id: str, table_number: int):
    id = session_id
    try:
        sql_query = """
            SELECT id, table_number, items, quantities, prices
            FROM ck-eams.orderaibot.order_items
            WHERE id = @id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", id)
            ]
        )

        # Run the query job
        query_job = client.query(sql_query, job_config=job_config)

        # Fetch the results
        results = query_job.result()
        
        # Process the results
        order_summary_list = [{'items': row[2], 'quantities': row[3], 'prices': row[4]} for row in results]
#         
        # Print the order summary list (for debugging purposes)
        print("Order Summary:")
        print(order_summary_list)

        # Insert order (not sure why this is here, you might need to modify this part)
        # insert_order(session_id)

        return order_summary_list
    except Exception as e:
        print(f"Error: {e}")
        return [{"error": "Order summary not found"}]

@app.get("/get_order_final_summary", response_model=list[dict])
def get_order_final_summary_from_db(table_number: int):
    try:  
        sql_query = """
            SELECT session_ids
            FROM `ck-eams.orderaibot.tables`
            WHERE table_number = @table_number
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table_number", "STRING", str(table_number))
            ]
        )

        # Run the query job
        query_job = client.query(sql_query, job_config=job_config)

        # Fetch the results
        results = query_job.result()
        
        # Process the results to get all session IDs for the given table number
        session_ids = [row[0] for row in results]

        print("Payment session_ids:", session_ids)
        
        # Initialize variables to store final list and total bill
        final_list = []
        total_bill = 0
        session_ids = session_ids[0]
        # Loop through each session ID to fetch order details
        for session_id in session_ids:
            print(session_id)
            final_query = """
                SELECT items, quantities, prices
                FROM `ck-eams.orderaibot.order_items`
                WHERE id = @session_id
            """
            final_job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("session_id", "STRING", session_id)]
            )

            # Run the query job
            final_query_job = client.query(final_query, job_config=final_job_config)

            # Fetch the results
            final_results = final_query_job.result()
            
            # Process the results and calculate total bill
            order_details = [{'items': row[0], 'quantities': row[1], 'prices': row[2]} for row in final_results]
            final_list.extend(order_details)
            
        print("Final Order Summary:")
        print(final_list)

        return final_list
    except Exception as e:
        print(f"Error: {e}")
        return [{"error": "Order summary not found"}]



# @app.get("/get_order_final_summary", response_model=list[dict])
# def get_order_final_summary_from_db(table_number: int):
#     try:
#         # Define the SQL query
#         sql_query = """
#             SELECT items, quantities, prices
#             FROM `ck-eams.orderaibot.order_items`
#             WHERE id IN (
#                 SELECT session_ids
#                 FROM `ck-eams.orderaibot.tables`
#                 WHERE table_number = @id
#             )
#         """

#         # Set up the query parameters
#         job_config = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("id", "STRING", id)
#             ]
#         )

#         # Run the query job
#         query_job = client.query(sql_query, job_config=job_config)

#         # Fetch the results
#         results = query_job.result()

#         # Process the results
#         order_summary_list = [{'items': row[0], 'quantities': row[1], 'prices': row[2]} for row in results]

#         # Print the order summary list (for debugging purposes)
#         print("Order Summary:")
#         print(order_summary_list)

#         return order_summary_list
#     except Exception as e:
#         print(f"Error: {e}")
#         return [{"error": "Order summary not found"}]


# @app.get("/get_order_summary", response_model=list[dict])
# def get_order_summary_from_db(session_id: str, table_number:int):
#     id=session_id
#     try:
#         sql_query="""
#             SELECT item_name, quantity, price 
#             FROM ck-eams.dosabot.order_items 
#             WHERE id = @id
#         """
#         job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("id", "STRING",id),
           
#         ])

#         # Run the query job
#         query_job = client.query(sql_query, job_config=job_config)

#         # Wait for the job to complete (optional)
#         order_summary=query_job.result()

#         # Convert the data into a list of dictionaries
#         order_summary_list = [{'item_name': row[0], 'quantity': row[1], 'price': row[2]} for row in order_summary]
#         print("orderSummary :  ")
#         print(order_summary_list)
#         insert_order(session_id)
#         return order_summary_list
#     except Exception as e:
#         print(f"Error: {e}")
#         return [{"error": "Order summary not found"}]


# # Function to create the "orders" table and insert session_id and totalprice
# def insert_order(session_id):

#         total_price=calculate_total_price(session_id)
#         id=session_id
#         # Execute the SQL statement to insert data
#         sql_query="""
#             INSERT INTO ck-eams.dosabot.orders (id, total_price)
#             VALUES (@id, @total_price)
#             """
#         job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("id", "STRING",id),
#             bigquery.ScalarQueryParameter("total_price", "STRING",total_price),
           
#         ])

#         # Run the query job
#         query_job = client.query(sql_query, job_config=job_config)

#         # Wait for the job to complete (optional)
#         query_job.result()
#         print("Inserted into orders successfully")
        
#         payment(session_id)
        
        
        

# def calculate_total_price(session_id):
#     id=session_id
#     sql_query="""SELECT SUM(CAST(quantity AS INT64) * CAST(price AS INT64))
#                   FROM ck-eams.dosabot.order_items
#                   WHERE id = @id"""


#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("id", "STRING",id),
           
#         ])

#     # Run the query job
#     query_job = client.query(sql_query, job_config=job_config)

#     # Wait for the job to complete (optional)
#     results=query_job.result()
#     total_price =[ row[0] for row in results]
#     print(total_price)
#     print(total_price[0])
#     return total_price[0]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)