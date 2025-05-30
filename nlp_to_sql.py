# nlp_to_sql.py
import os
import requests
import json
import re

class NLPtoSQL:
    def __init__(self, api_key=None):
        # Get API key from environment variable or use provided key
        self.api_key = api_key='AIzaSyD12oAj9I865-1QX-NMVFkenkfPzixYyqc'
        if not self.api_key:
            raise ValueError("API key must be provided or set as GEMINI_API_KEY environment variable")
            
        # Database schema information to help the LLM generate accurate SQL
        self.schema = """
        Database Schema:
        - users: id (INT), username (VARCHAR), email (VARCHAR), password (VARCHAR), name (VARCHAR), created_at (TIMESTAMP)
        - grades: id (INT), user_id (INT), subject (VARCHAR), score (FLOAT), max_score (FLOAT), grade_letter (VARCHAR), created_at (TIMESTAMP)
        
        Foreign keys:
        - grades.user_id references users.id
        """
        
    def generate_sql(self, natural_language_query):
        """Convert natural language query to SQL query using Gemini API"""
        
        # Construct the prompt
        prompt = f"""
        You are an SQL expert. Convert the following natural language query to a valid MySQL SQL query.
        Use the following database schema for reference:
        
        {self.schema}
        
        Natural language query: "{natural_language_query}"
        
        Return ONLY the raw SQL query with absolutely no markdown formatting, no backticks, no 'sql' language identifier, and no additional text or explanation. The response should contain only valid SQL that can be executed directly.
        """
        
        try:
            # API call to Gemini
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={self.api_key}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            # Make the API request with additional error handling
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=10
                )
                
                # Print the raw response for debugging
                print(f"Status code: {response.status_code}")
                print(f"Response headers: {response.headers}")
                
                # Check if the response is JSON by examining the content type
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    print(f"Unexpected content type: {content_type}")
                    print(f"Response body: {response.text[:500]}...")  # Print first 500 chars for debugging
                    return None, f"API returned non-JSON response with content type: {content_type}"
                
                # Try to parse JSON
                try:
                    response_json = response.json()
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {str(e)}")
                    print(f"Response body: {response.text[:500]}...")  # Print first 500 chars for debugging
                    return None, f"Failed to parse API response as JSON: {str(e)}"
                
            except requests.exceptions.RequestException as e:
                return None, f"API request error: {str(e)}"
            
            if response.status_code == 429:
                return None, "API rate limit exceeded. Please check your quota."
            elif response.status_code != 200:
                error_message = response_json.get('error', {}).get('message', 'Unknown error')
                return None, f"Error: {response.status_code} - {error_message}"
            
            # Extract the SQL query from the response
            if 'candidates' not in response_json or not response_json['candidates']:
                return None, "API response did not contain expected 'candidates' field"
                
            if 'content' not in response_json['candidates'][0] or 'parts' not in response_json['candidates'][0]['content']:
                return None, "API response has unexpected structure"
                
            if not response_json['candidates'][0]['content']['parts']:
                return None, "API response contains empty 'parts' field"
            
            raw_text = response_json['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean the SQL by removing markdown formatting
            sql_query = self._clean_markdown_formatting(raw_text)
            
            # Simple validation (can be expanded)
            if not self._validate_sql(sql_query):
                return None, "Generated SQL query contains potentially unsafe operations"
                
            return sql_query, None
            
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            return None, f"Error generating SQL: {str(e)}\n{trace}"
    
    def _clean_markdown_formatting(self, text):
        """Remove markdown formatting from the SQL response"""
        # Remove markdown code block formatting
        clean_text = re.sub(r'```sql\s*|\s*```', '', text)
        clean_text = re.sub(r'```mysql\s*|\s*```', '', clean_text)
        clean_text = re.sub(r'```\s*|\s*```', '', clean_text)
        
        # Remove any other markdown syntax that might be present
        clean_text = clean_text.strip()
        
        return clean_text
    
    def _validate_sql(self, sql_query):
        """Basic validation to prevent unsafe SQL queries"""
        # Convert to lowercase for safer checking
        sql_lower = sql_query.lower()
        
        # Check for potentially dangerous operations
        dangerous_keywords = ["drop table", "drop database", "truncate table", "delete from", "alter table"]
        
        # Allow select queries and safe operations
        if sql_lower.startswith("select") or sql_lower.startswith("show"):
            return True
            
        # Block potentially dangerous operations for regular users
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                return False
                
        return True
            
    def execute_query(self, sql_query, mysql_connection):
        """Execute the SQL query and return results"""
        try:
            cursor = mysql_connection.cursor()
            cursor.execute(sql_query)
            
            # For SELECT queries, fetch and return results
            if sql_query.lower().strip().startswith("select"):
                results = cursor.fetchall()
                # Get column names
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return {"columns": columns, "data": results}, None
                return {"columns": [], "data": []}, None
                
            # For other queries (INSERT, UPDATE, etc.)
            mysql_connection.commit()
            return {"affected_rows": cursor.rowcount}, None
            
        except Exception as e:
            return None, f"Error executing SQL: {str(e)}"
        finally:
            cursor.close()

# Example usage with a fallback to a hardcoded SQL generator if the API fails
class FallbackSQLGenerator:
    def __init__(self):
        self.schema = {
            "tables": {
                "users": ["id", "username", "email", "password", "name", "created_at"],
                "grades": ["id", "user_id", "subject", "score", "max_score", "grade_letter", "created_at"]
            },
            "relationships": [
                {"from": "grades.user_id", "to": "users.id"}
            ]
        }
    
    def generate_sql(self, query):
        """Very basic NL to SQL converter with simple pattern matching"""
        query = query.lower()
        
        # Simple pattern matching
        if "all users" in query:
            return "SELECT * FROM users;", None
        elif "all grades" in query:
            return "SELECT * FROM grades;", None
        elif re.search(r"grades?.+subject", query) or re.search(r"subject.+grades?", query):
            subject = None
            
            # Try to extract subject from query
            subjects = ["math", "science", "english", "history", "physics", "chemistry", "biology"]
            for s in subjects:
                if s in query:
                    subject = s
                    break
                    
            if subject:
                return f"SELECT * FROM grades WHERE subject = '{subject.upper()}';", None
            else:
                return "SELECT subject, COUNT(*) as count FROM grades GROUP BY subject;", None
        else:
            # Default fallback
            return "SELECT * FROM grades LIMIT 10;", None

# Usage with fallback:
def get_sql_for_query(natural_language_query, gemini_api_key=None):
    # Try using Gemini first
    nlp_sql = NLPtoSQL(api_key=gemini_api_key)
    sql_query, error = nlp_sql.generate_sql(natural_language_query)
    
    # If Gemini fails, use the fallback
    if error:
        print(f"Gemini API error: {error}")
        print("Using fallback SQL generator...")
        fallback = FallbackSQLGenerator()
        sql_query, error = fallback.generate_sql(natural_language_query)
    
    return sql_query, error