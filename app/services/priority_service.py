import requests
from app.config import PRIORITY_API_URL, HTTP_CONNECT_TIMEOUT_S, HTTP_READ_TIMEOUT_S


class PriorityService:
    """Service to fetch user priority from external API"""
    
    def get_user_priority(self, user_id: str) -> str:
        """
        Call external API to get user's priority level.
        
        Args:
            user_id: User identifier
            
        Returns:
            Priority level: "high", "medium", or "low"
            Defaults to "medium" on error or invalid response
        """
        try:
            response = requests.get(        # This is basically the backend master to get the user priroty.
                f"{PRIORITY_API_URL}/users/{user_id}/priority",
                timeout=(HTTP_CONNECT_TIMEOUT_S, HTTP_READ_TIMEOUT_S)
            )
            response.raise_for_status()
            data = response.json()
            priority = data.get("priority", "medium").lower()
            
            # Validate priority value
            if priority not in ["high", "medium", "low"]:
                print(f"Invalid priority '{priority}' for user {user_id}, defaulting to medium")
                return "medium"
            
            return priority
            
        except requests.exceptions.Timeout:
            print(f"Timeout fetching priority for user {user_id}, defaulting to medium")
            return "medium"
        except requests.exceptions.RequestException as e:
            print(f"Error fetching priority for user {user_id}: {e}, defaulting to medium")
            return "medium"
        except Exception as e:
            print(f"Unexpected error fetching priority for user {user_id}: {e}, defaulting to medium")
            return "medium"
