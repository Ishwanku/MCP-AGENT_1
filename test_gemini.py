import os
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path

# Load environment variables
load_dotenv()

def test_gemini_api():
    print("Testing Gemini API connection...")
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        return False
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create a model instance
        model = genai.GenerativeModel('gemini-pro')
        
        # Test with a simple prompt
        test_prompt = "Hello, can you confirm you're working?"
        response = model.generate_content(test_prompt)
        
        print("\nAPI Test Results:")
        print("-----------------")
        print("Status: Success")
        print("Response:", response.text)
        print("\nGemini API is working correctly!")
        return True
        
    except Exception as e:
        print("\nAPI Test Results:")
        print("-----------------")
        print("Status: Failed")
        print("Error:", str(e))
        return False

if __name__ == "__main__":
    test_gemini_api() 