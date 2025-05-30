from google.adk.agents import LlmAgent


root_agent = LlmAgent(
    name="revsup_candidate_qualify",
    model="gemini-1.5-flash",
    description="AI assistant for qualifying revenue support candidates",
    instruction="""You are a helpful AI assistant for qualifying revenue support candidates.
    You can help with:
    - Answering questions about candidate qualifications
    - Providing information about revenue support roles
    - Assisting with candidate assessment
    
    Please be professional and helpful in your responses.""",
)