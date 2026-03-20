# Travel Assistant Workshop — Runbook

## Part 1: Setup & Deployment

### 1.1 Open Kiro

Open Kiro 

### 1.2 Clone the Repository

Create a folder in your laptop. 

Clone repo - https://github.com/mankale/travel-assistant-workshop

### 1.3 Deploy the Baseline Project

Once cloning is completed, use below prompt for deployment - 

"go through this file - travel-assistant-workshop/README.md . understand the dependencies and deployment steps. except clean up script and backend.py , run all steps. make sure to export AWS_DEFAULT_REGION=us-east-1 before running each script." 

### 1.4 Start the Frontend

Once the deployment is complete, open another terminal window and 

cd travel-assistant-workshop
cd frontend && python backend.py

Frontend is accessible on http://localhost:8000 . Open this in your browser. 

---

## Part 2: Testing Flight Search & Booking

### 2.1 Search Flights

"show me the flight options for new york to los angeles on 10th April" 

### 2.2 Book a Flight

"Book this flight" 

### 2.3 Search with Date Range

"show me all the flights originating from Sydney to Singapore from 15th to 30th April"

### 2.4 Book a Specific Airline

"like that Singapore Airlines one, book it."

### 2.5 Search Another Route

"Display all flights from Bangalore to London for 1st May"

### 2.6 Check Business Class Availability

"Ok, how about Business class on this. Do they have it?"

### 2.7 Book Business Class

"yes, book a business class."

---

## Part 3: Building Hotel Search Feature

### 3.1 Explore Hotel Data

"ok, now we have a travel-assistant-workshop/hotel-data.json data. go through it and understand the intent of it."

### 3.2 Create Search Hotels Function

"ok , on similar lines of travel-assistant-workshop/search_flights.py lets create a search_hotels.py function. build a lambda zip package also in travel-assistant-workshop/lambdas/ . this function will look for hotel details from the json data. the required input parameter is city, the rest are optional(check in date, check out date)."

### 3.3 Create Book Hotels Function

"lets create a hotel booking function as well now. this hotel simply returns "Hotel booking is successfully done!" on invoking. take travel-assistant-workshop/lambdas/book_flights_lambda.zip as a reference."

### 3.4 Deploy & Register Hotel Functions

"now deploy the newly created search hotel and book hotel functions. once deployed, add these lambda functions as targets to existing AgentCore Gateway. you will get details of Gateway ARN in travel-assistant-workshop/config.json."

### 3.5 Create Hotel Agent & Update Supervisor

"now, we need to also create and deploy a new agent to search/book hotels. this agent will use same AgentCore Gateway endpoint as that of flight agent. this new agent will be invoked by existing supervisor agent. update system prompt of supervisor agent to handle both flight and hotel operations now. redeploy the supervisor agent once done."

### 3.6 Update Frontend for Hotels

"update the travel-assistant-workshop/frontend/ to display hotel search/booking capability along with existing flights."

---

## Part 4: Testing Hotel Search & Booking

### 4.1 Search Hotels

"Hey, look for hotels in New York for 10th April checkin"

### 4.2 Filter by Star Rating

"show only 5-star hotels"

### 4.3 Pick the Best Value

"go for the most frugal option among 5-star hotels"
