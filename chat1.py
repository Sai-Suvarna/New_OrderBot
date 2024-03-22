import openai
import pandas as pd
import os
import random
from dotenv import load_dotenv
import json
from twilio.rest import Client
import re
import uuid
import qrcode
import copy
from google.cloud import bigquery
import ast
from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    HTTPException,
    status,
    Cookie,
)


project_id = 'ck-eams'

# Initialize a BigQuery client
client = bigquery.Client(project=project_id)
load_dotenv()

api_key = os.getenv("API_KEY")
openai.api_key = api_key


context = [ {'role':'system', 'content':"""
You are OrderBot, an automated service to collect orders for restaurants. \
Your  goal is to place orders and explain the users about the food items in your menu. \
you can also recommend the best food items whenever needed \
You should respond only to take the orders and for all other queries you should not respond since you are an orderbot. \
You first greet the customer as 'Hello I am an orderbot', and then collect the order.\
ask if they want to add anything else to their order \
You wait to collect the entire order, then summarize it, all amount are in  rupees \
Make sure to clarify all options, extras  uniquely \
identify the item from the menu.\
If the item ordered by the user does not match with any item in the menu, then ask the user to check and re-enter the name of the item in a polite manner. \
If the item ordered by the user nearly matches with any one item in the menu , then provide the matched item names in the menu to the user and ask the user politely to confirm the item name to order \
If the name of item ordered by the user matches with more than one item in the menu, then ask the user to check and re-enter the correct item name as per the menu he/she wants in a polite manner or you have to suggest the matching item names and then ask the user to  choose the item \
You should respond in a short and  very conversational friendly style. \
Display the summary of items ordered whenever asked in a clearly understandable way. \
As an orderbot it is your strict responsibility to store the orders when prompted . This is very important task of yours\
You should not tell that no order is found in the chat, even if the  user has already ordered some items \
You have to store multiple items in a single order , if ordered \
Ask the customer to mention the quantity of the items in a polite way if not mentioned, otherwise do not  ask \
If the user wants or seems to add nothing to order, then tell the customer the summary of items  ordered in a detailed way, and then ask the user to confirm by asking the user to type 'confirm'\
Only if the user types 'confirm' or 'Confirm' or 'CONFIRM', then you must display the order summary clearly , also tell the user that his/her order is placed successfully and then you should prompt the user to click on view order button to view their order \
You should take orders only for the items that are included in your menu. \
Tell all the available categories mentioned under "Available categories" like "STARTERS - VEGETARIAN", "STARTERS - NON VEGETARIAN" , "SOUPS - VEGETARIAN" , "SOUPS - NON-VEGETARIAN"  ,etc present in the menu if asked \
You should cross check the names of items present in the menu . If item ordered by the user matches partially then ask the user to enter the name of item completely as per the menu in a polite manner .\
Ignore the lowercase and uppercase, just compare the item entered by the user and the item present in the menu\


Available categories \
HOT AND COLD BEVERAGES,
SOUPS - VEGETARIAN,
SOUPS - NON-VEGETARIAN,
STARTERS - VEGETARIAN,
STARTERS - NON VEGETARIAN,
MAIN COURSE - VEGETARIAN,
MAIN COURSE - NON VEGETARIAN,
RICE AND NOODLES - VEGETARIAN, 
INDIAN BREADS,
SIZZLERS,
RICE AND NOODLES - NON VEGETARIAN,
DESSERTS \


The menu includes \

HOT AND COLD BEVERAGES
Iced Tea:  95 rupees
Fresh lime soda:  75 rupees
Cold coffee:  95 rupees
Lassi: 95 rupees
Milk shake : 95 rupees
Soft drink: 75 rupees
Soda: 75 rupees
Mineral water: 75 rupees
Tea: 75 rupees
Coffee: 75 rupees


SOUPS - VEG
Wonton Veg soup : 145 rupees
Manchow soup Veg: 145 rupees
Creamy style sweet corn soup Veg: 145 rupees
Hot and sour soup Veg: 145 rupees
Tom yum koong (Spice prawn soup) Veg: 145 rupees
Clear soup Veg: 145 rupees
Lemon Coriander Soup Veg: 145 rupees


SOUPS NON-VEG
Wonton soup Non-Veg : 145 rupees
Manchow soup  Non-Veg: 145 rupees
Creamy style sweet corn soup Non-Veg: 145 rupees
Hot and sour soup Non-Veg: 145 rupees
Tom yum koong (Spice prawn soup) Non-Veg: 145 rupees
Clear soup Non-Veg: 145 rupees
Lemon Coriander Soup Non-Veg: 145 rupees


STARTERS - VEGETARIAN
Makai Malai Sheek: 285 rupees
Dhingri ke Tikke: 285 rupees
Paneer Tikke Achari: 285 rupees
Vegetable platter: 285 rupees
Vegetable Sheek Kebab: 285 rupees
Sonde Aloo: 285 rupees
Spinach Manchurian: 285 rupees
Chilly crispy vegetables: 285 rupees
Sesame fingers: 285 rupees
Mushroom salt & pepper: 285 rupees
Golden fried baby corn: 285 rupees
Vegetable khadda: 325 rupees


STARTERS - NON VEGETARIAN
Chicken Tikka: 345 rupees
Murgh Malai kebab: 345 rupees
Chicken with garlic pepper: 345 rupees
Spice chicken Szechwan: 345 rupees
Crispy chicken: 345 rupees
Tandoori chicken (Half): 345 rupees
Kheema balls: 375 rupees
Lamb Manchurian: 375 rupees
Fish fingers: 345 rupees
Tandoori Pomfret: 895 rupees
Tandoori Vanjaram: 895 rupees
Prawn 'N' garlic butter: 425 rupees
Lasooni Jhinga (Jumbo Prawn): 1899 rupees
Chicken Khadda: 425 rupees


MAIN COURSE - VEGETARIAN
Paneer Baby Corn Masala: 345 rupees
Paneer Methi Chaman: 345 rupees
Malai Kofta: 345 rupees
Aloo Ghobi masala: 345 rupees
Vegetable Jalfrezi: 345 rupees
Stuffed capsicum masala: 345 rupees
Dal Makhani: 175 rupees
Dal fry: 175 rupees


MAIN COURSE - NON VEGETARIAN
Chicken Tikka masala: 375 rupees
Kadai chicken: 375 rupees
Chicken Chettinadu: 375 rupees
Rogan-e- Dosht: 425 rupees
Dhaba Gosht: 425 rupees
Sarson ki Machli: 375 rupees
Machi Amritsari: 375 rupees
Haldi Mirchi Jhinga: 475 rupees


INDIAN BREADS
Rumali Roti: 75 rupees
Butter Naan: 95 rupees
Tawa Paratha: 95 rupees
Roti: 75 rupees
Phulka (2 pcs): 75 rupees


SIZZLERS
Chicken in smoked Barbeque Sauce: 475 rupees
Desi Veg shaslik sizzler: 475 rupees


RICE AND NOODLES - VEGETARIAN 
Vegetable Biryani: 345 rupees
Peas Pulao: 345 rupees
Jeera Fried Rice: 345 rupees
Szechwan Fried Rice: 345 rupees
American Chopsuey: 345 rupees
Singapore Rice Noodles: 345 rupees


RICE AND NOODLES - NON VEGETARIAN
Murgh Biryani: 425 rupees
Gosht Biryani: 475 rupees
Chicken Fried Rice: 425 rupees
Singapore Rice Noodles: 425 rupees
American Chopsuey: 425 rupees
Mixed fried rice / noodles: 475 rupees


DESSERTS
Chocolate fondue: 475 rupees
Sizzling Brownie: 225 rupees
Drunken Prunes: 195 rupees
Blue Berry Cheese Cake: 195 rupees
Tiramisu: 195 rupees
Baked Alaska: 225 rupees
Banana Split: 195 rupees
Ice Cream: 175 rupees
Fruit Salad: 175 rupees
"""
} 
]

user_conversations={}

def get_completion_from_messages1(messages, model="gpt-3.5-turbo-0125", temperature=0.2):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )

    return response.choices[0].message["content"]

def add_user_message(session_id, message):
    if session_id not in user_conversations:
        context_copy = copy.deepcopy(context)
        user_conversations[session_id] = context_copy
    user_conversations[session_id].append({"role": "user", "content": message})


# Function to get the conversation history for a user
def get_user_conversation(session_id):
    return user_conversations.get(session_id, [])



def collect_messages_text1(msg,session_id, table_number):
    prompt=msg
    # print(user_conversations)
    add_user_message(session_id, msg)
    
    conversation = get_user_conversation(session_id)
    response = get_completion_from_messages1(conversation)
    
    user_conversations[session_id].append({"role": "assistant", "content": response})
    
    if(prompt=="confirm" or prompt=="Confirm" or prompt=="CONFIRM"):
        
        store_order_summary(session_id, table_number)
    return response



def store_order_summary(session_id, table_number):
    msg="""get the details of items ordered by the user from the chat and provide the order details in a python list containing tuples where each tuple contains item_name,quantity and price. 
    here price is the price of each item. If once 'confirm' or 'Confirm' or 'CONFIRM' is prompted, then display the summary of order clearly. 
    Don't include every item present in the chat. Include the items that are actually ordered by the user in the ordered list . please do it carefully."""
    add_user_message(session_id, msg)
    conversation = get_user_conversation(session_id)
    response = get_completion_from_messages1(conversation)
    user_conversations[session_id].append({"role": "assistant", "content": response})
    
    # Regular expression pattern to match a list of tuples
    pattern = r'\[.*?\]'

    # Use re.findall to extract all matching patterns
    matches = re.findall(pattern, response,re.DOTALL)
    extracted_list = []
    # Convert the matched string to a Python list of tuples
    if matches:
        extracted_list = eval(matches[0])  # Use eval to convert the string to a list
        print(extracted_list)
        KOT(extracted_list, table_number)
       
        id=session_id
        # Insert data into the table

        sql_query1 = """
            SELECT table_number, session_ids
            FROM ck-eams.orderaibot.tables
            WHERE table_number = @table_number
        """
        job_config1 = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table_number", "STRING", table_number)
            ]
        )

        # Run the query job
        query_job1 = client.query(sql_query1, job_config=job_config1)

        # Fetch the results
        results1 = query_job1.result()
        
        table_details = [{'table_number': row[0], 'session_ids': row[1]} for row in results1]
        session_ids = []
        session_ids.append(session_id)
        print("table details = ", table_details)
        if len(table_details) == 0:
            print("not found ")
            sql_query2="""INSERT INTO ck-eams.orderaibot.tables(table_number, session_ids)
                        VALUES (@table_number,@session_ids)"""
            job_config2 = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("table_number", "STRING", table_number),
                        bigquery.ArrayQueryParameter("session_ids", "STRING", session_ids),
                    ]
                )

            # Run the query job
            query_job2 = client.query(sql_query2, job_config=job_config2)
            
            # Wait for the job to complete (optional)
            query_job2.result()
            for row in query_job2.result():
                print(row)
                print("inserted into tables")

        else:
            print("found")
            sql_query3 = """SELECT  table_number, session_ids FROM ck-eams.orderaibot.tables
                    WHERE table_number = @table_number"""
            job_config3 = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_number", "STRING", table_number)
                ]
            )

            # Run the query job
            query_job3 = client.query(sql_query3, job_config=job_config3)

            # Fetch the results
            results3 = query_job3.result()
            
            # Process the results
            tables_list = [{'table_number': row[0], 'session_ids': row[1]} for row in results3]
            session_ids = []
            for row in tables_list:
                # Check if the 'session_ids' field is a list and not None or another data type
                if isinstance(row['session_ids'], list):
                    # Extend the session_ids list with the session_ids of the current row
                    session_ids.extend(row['session_ids'])

            print("session_ids retrieved = ",session_ids)

            session_ids.append(session_id)
            

            delete_query = """DELETE FROM `ck-eams.orderaibot.tables`
                            WHERE table_number = @table_number
                            """
            job_config_del = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_number", "STRING", table_number)
                ]
            )

            # Run the query job
            query_job_del= client.query(delete_query, job_config=job_config_del)

            
            
            sql_query4="""INSERT INTO ck-eams.orderaibot.tables(table_number, session_ids)
                        VALUES (@table_number,@session_ids)"""
            job_config4 = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("table_number", "STRING", table_number),
                        bigquery.ArrayQueryParameter("session_ids", "STRING", session_ids),
                    ]
                )

            # Run the query job
            query_job4 = client.query(sql_query4, job_config=job_config4)
            
            # Wait for the job to complete (optional)
            query_job4.result()
            for row in query_job4.result():
                print("retrieved and inserted successfully")
                print(row)


        total = 0
        for data in extracted_list:
            items, quantities, prices = data
            
        
            sql_query="""INSERT INTO ck-eams.orderaibot.order_items(id, table_number, items, quantities, prices)
                        VALUES (@id, @table_number,@items,@quantities,@prices)"""

            job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("id", "STRING", id),
                        bigquery.ScalarQueryParameter("table_number", "STRING", table_number),
                        bigquery.ScalarQueryParameter("items", "STRING", items),
                        bigquery.ScalarQueryParameter("quantities", "INT64", quantities),
                        bigquery.ScalarQueryParameter("prices", "INT64", prices),
                        
                    ]
                )

            # Run the query job
            query_job = client.query(sql_query, job_config=job_config)
            
            # Wait for the job to complete (optional)
            query_job.result()
            for row in query_job.result():
                print(row)
            payment(table_number, session_id)
        

        # for data in extracted_list:
        #         item_name, quantity, price = data
        #         # print(item_name, quantity, price) 

        #         sql_query="""
        #             INSERT INTO ck-eams.dosabot.order_items(id, item_name, quantity, price)
        #             VALUES (@id,@item_name,@quantity,@price)"""

        #         job_config = bigquery.QueryJobConfig(
        #                 query_parameters=[
        #                     bigquery.ScalarQueryParameter("id", "STRING", id),
        #                     bigquery.ScalarQueryParameter("item_name", "STRING", item_name),
        #                     bigquery.ScalarQueryParameter("quantity", "STRING", quantity),
        #                     bigquery.ScalarQueryParameter("price", "STRING", price)
        #                 ]
        #             )

        #         # Run the query job
        #         query_job = client.query(sql_query, job_config=job_config)
        #         print()
        #         # Wait for the job to complete (optional)
        #         query_job.result()
        #         for row in query_job.result():
        #             print(row)
    else:
        print("No order details found in the text. Can you please order again.")    


def KOT(order_list, table_number):
    print("KOT")
    print("Table Number : ", table_number)
    
    # Create a list of dictionaries with formatted item names
    data = []
    for item_name, quantity, price in order_list:
    # Truncate item names to 20 characters and pad with spaces for alignment
        formatted_name = item_name[:20].ljust(20)  # Left-justify with spaces
        data.append({"Item Name": formatted_name, "Quantity": quantity, "Price": price})  # Add price column

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(data)

    # Control display options for a cleaner output
    pd.set_option('display.max_colwidth', None)  # Disable column width truncation
    print(df.to_string(index=False))


    
def create_bill_number():
    random_code = ''.join(random.choices('0123456789', k=15))

    return random_code



def payment(table_number, session_id):
    upi_id = "7013049899@ybl"   #Dosa owner UPI
    note = "Payment for your order"   #List of items ordered by customer
    

    sql_query10 = """SELECT  table_number, session_ids FROM ck-eams.orderaibot.tables
                    WHERE table_number = @table_number"""
    job_config10 = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("table_number", "STRING", table_number)
        ]
    )

    # Run the query job
    query_job10 = client.query(sql_query10, job_config=job_config10)

    # Fetch the results
    results10 = query_job10.result()
    
    # Process the results
    tables_list = [{'table_number': row[0], 'session_ids': row[1]} for row in results10]
    session_ids = []
    for row in tables_list:
        # Check if the 'session_ids' field is a list and not None or another data type
        if isinstance(row['session_ids'], list):
            # Extend the session_ids list with the session_ids of the current row
            session_ids.extend(row['session_ids'])

    print("payment session_ids: ", session_ids)
    bill = 0
    for id in session_ids:
        final_query = """SELECT  items, quantities, prices FROM ck-eams.orderaibot.order_items
                    WHERE id = @id"""
        final_job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", id)])

        # Run the query job
        final_query_job = client.query(final_query, job_config=final_job_config)

        # Fetch the results
        final_results = final_query_job.result()
        print("rows = ")
        final_list = [{'items': row[0], 'quantities': row[1], 'prices': row[2]} for row in final_results]
        for row in final_list:
            print(row)
            bill += row['quantities']*row['prices']

        
    # sql_query="""SELECT total_price 
    #     FROM ck-eams.dosabot.orders 
    #     WHERE id = @id
    # """
    
    # job_config = bigquery.QueryJobConfig(
    #     query_parameters=[
    #         bigquery.ScalarQueryParameter("id", "STRING",id),
    #     ])

    #     # Run the query job
    # query_job = client.query(sql_query, job_config=job_config)
    # money_value=[row[0] for row in query_job.result()]

    # Formulate UPI URL
    upi_url = f"upi://pay?pa={upi_id}&pn=&mc=&tid=&tr=&tn={note}&am={bill}&cu=INR"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)

    bill_number = create_bill_number()
    

    # Create and save QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    # qr_img.save("static/upi_qr_code.png")
    qr_img.save(f"static/upi_qr_code_{session_id}.png")
     
