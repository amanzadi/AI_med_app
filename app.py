import json
import requests
import streamlit as st
from db import ClinicDB
from agno.agent import Agent
from datetime import datetime
from bs4 import BeautifulSoup
from agno.tools.sql import SQLTools
from sqlalchemy import create_engine
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools 

# Initialize Database
db = ClinicDB()
db_url = "sqlite:///clinic.db"
engine = create_engine(db_url)

# Define Custom Tools
class FindDoctorsInClinicTool:
    def __init__(self, db):
        self.db = db
    name = "find_doctors_in_clinic"
    description = "Checks if a doctor with a given name or specialty exists in our clinic's *internal database*. Use this AFTER attempting a general search for doctors."
    def run(self, search_query: str):
        doctors = self.db.get_doctors()
        results = []
        if search_query.isdigit():
            for doc in doctors:
                if doc['id'] == int(search_query):
                    results.append(doc)
        else:
            search_lower = search_query.lower()
            for doc in doctors:
                full_name = f"{doc['first_name']} {doc['last_name']}".lower()
                if (search_lower in full_name or
                    search_lower in doc['specialty'].lower() or
                    search_lower in f"dr. {doc['last_name']}".lower()):
                    results.append(doc)
        
        if not results:
            return {"message": f"No doctors matching '{search_query}' found in *our clinic's database*.", "doctors_found": []}
        
        return {"message": f"Found {len(results)} doctor(s) matching '{search_query}' in *our clinic's database*.", "doctors_found": results}

class GetAvailabilityTool:
    def __init__(self, db):
        self.db = db
    name = "get_doctor_availability"
    description = "Get available appointment slots for a specific doctor (by ID) on a specific date (format: YYYY-MM-DD) *from our clinic's database*."
    def run(self, doctor_id: int, date: str):
        # Validate doctor_id exists in database
        doctors = self.db.get_doctors()
        doctor_exists = any(doc['id'] == doctor_id for doc in doctors)
        if not doctor_exists:
            return {"error": f"Doctor with ID {doctor_id} not found in our clinic's database. I can only check availability for doctors registered with us."}
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid date format: {date}. Please use YYYY-MM-DD format."}
        
        slots = self.db.get_available_slots(doctor_id, date)
        
        if slots:
            formatted_slots = [datetime.strptime(slot, "%Y-%m-%d %H:%M").strftime("%a, %b %d %Y at %I:%M %p") for slot in slots]
            return {
                "doctor_id": doctor_id,
                "date": date,
                "available_slots": formatted_slots,
                "count": len(formatted_slots)
            }
        
        return {
            "doctor_id": doctor_id,
            "date": date,
            "available_slots": [],
            "count": 0,
            "message": f"No available slots found for doctor ID {doctor_id} on {date} in our clinic."
        }

class BookAppointmentTool:
    def __init__(self, db):
        self.db = db
    name = "book_appointment"
    description = "Book an appointment with a doctor (by ID) at a specific time slot *in our clinic's system*. Requires patient ID."
    def run(self, doctor_id: int, slot: str, emergency: bool = False, patient_id: int = None):
        if patient_id is None:
            return {"error": "Patient ID is required to book an appointment."}
        
        # Validate doctor_id exists in database
        doctors = self.db.get_doctors()
        doctor_exists = any(doc['id'] == doctor_id for doc in doctors)
        if not doctor_exists:
            return {"error": f"Doctor with ID {doctor_id} not found in our clinic's database. I can only book appointments for doctors registered with us."}
            
        # Validate patient_id exists in database
        patient = self.db.get_patient_by_id(patient_id)
        if not patient:
            return {"error": f"Patient with ID {patient_id} not found in our database."}
        
        try:
            # Parse the slot into datetime object
            slot_dt = datetime.strptime(slot, "%a, %b %d %Y at %I:%M %p")
            
            # Check if slot is actually available
            date_str = slot_dt.strftime("%Y-%m-%d")
            all_slots = self.db.get_available_slots(doctor_id, date_str)
            if not all_slots:
                return {"error": f"No available slots for doctor ID {doctor_id} on {date_str} in our clinic."}
                
            # Convert to same format for comparison
            slot_db_format = slot_dt.strftime("%Y-%m-%d %H:%M")
            if slot_db_format not in all_slots:
                return {"error": f"The requested time slot is not available for doctor ID {doctor_id}."}
            
            # Book the appointment
            confirmation = self.db.book_appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_time=slot_dt.isoformat(),
                is_emergency=emergency
            )
            
            # Get doctor info to include in response
            doctor_info = None
            for doc in doctors:
                if doc['id'] == doctor_id:
                    doctor_info = doc
                    break
            
            # Format confirmation nicely
            return {
                "status": "success",
                "confirmation_id": confirmation["id"],
                "doctor": doctor_info,
                "patient": patient,
                "appointment_time": slot,
                "is_emergency": emergency,
                "message": f"Appointment successfully booked with Dr. {doctor_info['last_name']} on {slot}."
            }
            
        except ValueError as e:
            return {"error": f"Invalid time slot format: {slot}. Error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to book appointment: {str(e)}"}

class HandleEmergencyTool:
    def __init__(self, db):
        self.db = db
    name = "handle_emergency"
    description = "Find earliest available appointment for emergency cases in a specific specialty *within our clinic's database*."
    def run(self, specialty: str, date: str):
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid date format: {date}. Please use YYYY-MM-DD format."}
            
        # Get doctors by specialty
        doctors = self.db.get_doctors(specialty)
        if not doctors:
            return {"error": f"No doctors specializing in '{specialty}' found in our clinic database."}
        
        earliest_slot = None
        selected_doctor = None
        
        for doctor in doctors:
            slots = self.db.get_available_slots(doctor['id'], date)
            if slots:
                slots_dt = [datetime.strptime(s, "%Y-%m-%d %H:%M") for s in slots]
                current_earliest = min(slots_dt)
                if not earliest_slot or current_earliest < earliest_slot:
                    earliest_slot = current_earliest
                    selected_doctor = doctor
        
        if not earliest_slot:
            return {
                "error": f"No available emergency slots for {specialty} specialists on {date} in our clinic.",
                "specialty": specialty,
                "date": date,
                "doctors_checked": len(doctors)
            }
            
        return {
            "doctor": selected_doctor,
            "slot": earliest_slot.strftime("%a, %b %d %Y at %I:%M %p"),
            "specialty": specialty,
            "date": date
        }

class BillingSearchTool:
    name = "search_billing_info"
    description = "Search for billing information on dr-bill.ca website using web search."
    def run(self, query: str):
        
        try:
            url = f"https://www.dr-bill.ca/?s={query}" # Simple search query param example
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            # Improved scraping: focus on article content or specific divs for relevance
            # This is a very basic example; a real-world scraper would need more precise selectors
            for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']):
                text = element.get_text().strip()
                if query.lower() in text.lower() and len(text) > 50: # Avoid very short irrelevant snippets
                    results.append(text)
            if not results:
                return {"info": f"No detailed billing information found for '{query}' on dr-bill.ca. You might need to browse the site directly."}
            return {
                "results": results[:3], # Limit results to top 3 relevant snippets
                "source": url
            }
        except Exception as e:
            return {"error": f"Failed to search billing information: {str(e)}. This might be a temporary issue or the website structure has changed."}


# SQLHelperTool remains useful for internal database schema introspection/queries
class SQLHelperTool:
    def __init__(self, db):
        self.db = db
    name = "sql_helper"
    description = "Get schema information and run safe SQL queries on the internal clinic database."
    def run(self, action: str = "schema", query: str = None):
        if action == "schema":
            return {
                "tables": {
                    "doctors": ["id", "first_name", "last_name", "specialty"],
                    "patients": ["id", "first_name", "last_name", "email", "phone"],
                    "appointments": ["id", "patient_id", "doctor_id", "appointment_time", "is_emergency"]
                },
                "message": "These are the tables and columns available in our *internal clinic database*. Use these exact column names in your SQL queries."
            }
        elif action == "query" and query:
            try:
                results = []
                with engine.connect() as connection:
                    result = connection.execute(query)
                    keys = result.keys()
                    for row in result:
                        results.append(dict(zip(keys, row)))
                return {
                    "success": True,
                    "results": results,
                    "count": len(results)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": "SQL query failed. Make sure you're using the correct column names for our internal database."
                }
        else:
            return {"error": "Invalid action. Use 'schema' to get database schema or 'query' to run a SQL query."}

# Create Tool Instances
tools = [
    FindDoctorsInClinicTool(db), # Renamed and re-purposed
    GetAvailabilityTool(db),
    BookAppointmentTool(db),
    HandleEmergencyTool(db),
    BillingSearchTool(),
    SQLHelperTool(db), 
    DuckDuckGoTools()
]

# Define Agent Instructions with improved clarity and context awareness
instructions = """
You are DocSplain, an intelligent medical appointment assistant. Follow these guidelines strictly:

1.  **Your Primary Goal**: Assist patients in finding doctors and booking appointments. Always strive to provide helpful information and clear next steps. **NEVER respond with "None" or vague, unhelpful statements.**

2.  **Doctor Search (General)**:
    * **When a user asks for a doctor (by name, specialty, or general inquiry like "find a heart doctor"):**
        * **Your first step should be to use your general knowledge and Gemini's search capabilities to find potential doctors online.** Formulate a natural language search query.
        * **Present these findings to the user.** Include names, specialties, and any relevant high-level information found.
        * **Crucially, explicitly state that these doctors may *not* be affiliated with *our clinic*.**
        * **Then, ask the user if they would like to check for availability with one of these doctors *within our clinic* or if they would like to search for doctors *specifically within our clinic's network*.** This is where `find_doctors_in_clinic` comes in.

3.  **Clinic-Specific Doctor Verification and Booking**:
    * **If the user identifies a doctor they found through your general search, or asks for a doctor by ID, or explicitly states they want a doctor *in our clinic*:**
        * Use the `find_doctors_in_clinic` tool to check if that doctor is registered in our local clinic database.
        * If the doctor is found in our clinic's database, then proceed with checking availability using `get_doctor_availability` and booking with `book_appointment`.
        * If the doctor is *not* found in our clinic's database, politely inform the user: "Dr. [Doctor Name] is not listed in our clinic's database for appointments. Would you like me to search for another doctor within our clinic, or perhaps a doctor with a specific specialty?"

4.  **Available Tools and Their Usage**:
    * `find_doctors_in_clinic(search_query: str)`: Use this tool *only* to confirm if a doctor exists in our clinic's internal database for appointment booking purposes. Do not use this for initial general doctor discovery.
    * `get_doctor_availability(doctor_id: int, date: str)`: Use this only for doctors confirmed to be in our clinic's database. The date *must* be in YYYY-MM-DD format.
    * `book_appointment(doctor_id: int, slot: str, emergency: bool, patient_id: int)`: Use this only for doctors confirmed to be in our clinic's database and with a valid time slot. Requires the patient_id from the session.
    * `handle_emergency(specialty: str, date: str)`: Use for finding the earliest available emergency appointment *within our clinic* for a given specialty. The date *must* be in YYYY-MM-DD format.
    * `search_billing_info(query: str)`: Use for inquiries about billing information on dr-bill.ca.
    * `sql_helper(action: str, query: str)`: Use this only for internal database schema inspection or safe SQL queries *if absolutely necessary* for a specific, complex internal data lookup that the other tools don't cover. Prioritize the higher-level tools.

5.  **Time Slot Handling**:
    * ALWAYS use the exact time slot format returned by `get_doctor_availability`.
    * NEVER create or suggest time slots that weren't explicitly returned by the tool.
    * If no slots are available on a requested date, suggest checking another date or ask if they'd like to find a different doctor.

6.  **Emergency Handling**:
    * For emergencies, use `handle_emergency` first if a specialty and date are provided.
    * If no emergency slots are available, politely inform the user and suggest checking another date or a broader specialty.

7.  **Patient Context**:
    * Always use the `patient_id` parameter passed to you for booking appointments.
    * Remember user preferences and context from chat history.

8.  **After Successful Booking**:
    * Provide a clear confirmation with doctor name, specialty, date/time, and appointment ID.
    * Mention that an email would be sent containing: Doctor's full name and specialty, Date and time, Appointment ID, Visit instructions.

9.  **Error Handling**:
    * If a tool returns an error, translate it into a user-friendly message.
    * Guide the user on how to retry or provide alternative options.
    * **Always ensure your response is helpful and never includes "None" or "No information found" without suggesting next steps.** If you can't find a doctor in your clinic, offer to use general search; if you can't book an appointment, explain why and offer alternatives.

10. **Billing Information**:
    * For billing inquiries, use `search_billing_info` or `DuckDuckGoTools()` to search https://www.dr-bill.ca for answers.
    * Specify that we primarily support AHCIP, MSP, and OHIP billing codes.

"""

# Create Agno Agent
agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    tools=tools,
    instructions=instructions,
    show_tool_calls=True,
    markdown=True
)

# Streamlit App Setup (remains largely the same)
st.set_page_config(page_title="DocSplain - Medical Appointment Assistant", layout="centered")
st.title("DocSplain - Medical Appointment Assistant")

# Initialize Session State for Chat Memory and Patient ID
if "messages" not in st.session_state:
    st.session_state.messages = []
if "patient_id" not in st.session_state:
    st.session_state.patient_id = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Function to get patient ID by email
def get_patient_id_by_email(email: str):
    patient = db.get_patient_by_email(email)
    if patient:
        return patient['id']
    return None

# --- Sidebar for Login ---
with st.sidebar:
    st.header("Patient Login")
    if not st.session_state.logged_in:
        email = st.text_input("Enter your email:", key="sidebar_email_input")
        if st.button("Login", key="sidebar_login_button"):
            if email:
                patient_id = get_patient_id_by_email(email)
                if patient_id:
                    st.session_state.patient_id = patient_id
                    st.session_state.logged_in = True
                    patient_info = db.get_patient_by_id(patient_id)
                    st.sidebar.success(f"Welcome, **{patient_info['first_name']}**!")
                    # Add initial welcome message to chat history if not already there
                    if not st.session_state.messages:
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"Welcome, **{patient_info['first_name']}**! How can I help you book an appointment today? You can search for doctors by name, specialty, or by describing your needs."
                        })
                    st.rerun() # Rerun to update the main chat area
                else:
                    st.sidebar.error("Patient not found. Please try again.")
            else:
                st.sidebar.warning("Please enter your email.")
    else:
        patient_info = db.get_patient_by_id(st.session_state.patient_id)
        st.write(f"Logged in as: **{patient_info['first_name']} {patient_info['last_name']}**")
        if st.button("Logout", key="sidebar_logout_button"):
            st.session_state.patient_id = None
            st.session_state.logged_in = False
            st.session_state.messages = [] # Clear chat history on logout
            st.experimental_rerun()

# --- Main Chat Area ---
if st.session_state.logged_in:
    # Display Chat Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input and Agent Interaction
    if prompt := st.chat_input("How can I help with your appointment today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Pass the entire chat history to the agent for memory
        chat_history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages]
        
        # Add additional context for the agent
        with st.spinner("DocSplain is thinking..."):
            try:
                response = agent.run(
                    prompt, 
                    chat_history=chat_history, 
                    patient_id=st.session_state.patient_id
                ) 
                
                st.session_state.messages.append({"role": "assistant", "content": response.content})
                with st.chat_message("assistant"):
                    st.markdown(response.content)
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}. Please try again."
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                with st.chat_message("assistant"):
                    st.markdown(error_message)
else:
    st.info("Please log in using the sidebar to start chatting and book appointments.")
    if not st.session_state.messages: # Add initial welcome message for unauthenticated users
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Welcome to DocSplain! Please log in using the sidebar to begin booking medical appointments."
        })
    # Display initial welcome message to chat history if not logged in
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
