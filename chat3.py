import openai
import os
from dotenv import load_dotenv
import json
from twilio.rest import Client

load_dotenv()

api_key = os.getenv("API_KEY")
openai.api_key = api_key

# Rest of your code using the OpenAI library

context = [ {'role':'system', 'content':"""
You are OrderBot, an automated service to collect orders for a street dosa. \
You first greet the customer as Hello I am an orderbot,Your first question after greeting the customer how may I help you today.This question is first question and fixed\
then collects the order, \
and then asks if it's a pickup or delivery. \
You wait to collect the entire order, then summarize it and check for a final, all amount are in Rupees \
time if the customer wants to add anything else. \
Make sure to clarify all options, extras and sizes uniquely \
identify the item from the menu.\
If it's a delivery, you ask for an address. \
Finally you collect the payment for all the orders.\
You should respond only to take the orders and for all other questions you should not respond since you are an orderbot. \
You respond in a short, very conversational friendly style. \
You should take orders only for the items that aree included in the following menu. \
Remember Pcs means pieces.Pronounce Pcs as pieces whenever you tell\
Remember /- indicates rupees.Pronounce Rupees wherever /- appears
The menu includes \

Jawar Idli (3 Pcs) 60/-
Multi Millet Idli (3 Pcs) 60/-
Barnyard Millet Idli (4 Pcs) 80/-
Foxtail Millet Idli (4 Pcs) 80/-
Bajra Millet Idli (4 Pcs) 80/-
Ragi Idli (3 Pcs) 60/-
Little Millet idli (4 Pcs) 80/-
Ragi Idli (2 Pcs) 40/-
Jowar Idli (2 Pcs) 40/-
Multi Millet Idli (2 Pcs) 40/-
Foxtail Millet Idli (2 Pcs) Koralu 40/-
Barnyard Millet Idli - 2 Pcs (oodalu) 40/-
Bajra Millet Idli (2 Pcs) 40/-
Ragi Idli (4 Pcs) 80/-
Little Millet Idli-2 Pcs (samalu) 40/-
Jawar Idli (3 Pcs) 60/-
Multi Millet Idli (3 Pcs) 60/-
Barnyard Millet Idli (4 Pcs) 80/-
Foxtail Millet idli (4 Pcs) 80/-
Bajra Millet Idli(4 Pcs) 80/-
Ragi Idli (3 Pcs) 60/-
Jawar Idli (4 Pcs) 80/-
Little Millet idli (4 Pcs) 80/-
Multi Millet Idli (4pcs) 80/-
Barnyard Millet Idli (3 Pcs) 60/-
Bajra Millet Idli(3 Pcs) 60/-
Foxtail Millet idli (3 Pcs) 60/-
Little Millet idli (3 Pcs) 60/-

"""} ]  # accumulate messages

def get_completion_from_messages3(messages, model="gpt-4-0314", temperature=0):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )
#   print(str(response.choices[0].message))
    return response.choices[0].message["content"]

def collect_messages_text3(msg):
    prompt = msg #.split(' ')
    print(prompt)
    # word='pickup'
    # if(word in prompt): 
    if(prompt=="pickup" or prompt=="delivery"):
        store_order_summary()
    context.append({'role':'user', 'content':f"{prompt}"})
    response = get_completion_from_messages3(context) 
    context.append({'role':'assistant', 'content':f"{response}"})
    return response


def store_order_summary():
    context.append({'role':'user','content':'Store the order in a json format with fields containing items,quantity and total price'})
    response = get_completion_from_messages3(context) 
    # context.append({'role':'assistant', 'content':f"{response}"})
    print(response)
    with open('order_summary.json', 'w') as json_file:
        json.dump(response, json_file)
    user_phone_number='+919347665827'
    send_whatsapp_message(user_phone_number, response)

def send_whatsapp_message(to, body):
    # Twilio credentials
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER") # Twilio's sandbox WhatsApp number

    client = Client(twilio_account_sid, twilio_auth_token)

    try:
        message = client.messages.create(
            from_=twilio_whatsapp_number,
            to='whatsapp:' + to,
            body=body
        )

        print('WhatsApp message sent successfully.')
        print(message.sid)
    except Exception as e:
        print('Error sending WhatsApp message:', str(e))
