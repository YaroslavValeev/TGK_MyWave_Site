from .google import GoogleService, init_google_services

# Export create_drive_link as a convenience function
def create_drive_link(file_id):
    """Convenience function to create a Google Drive link"""
    google_service = GoogleService()
    return google_service.create_drive_link(file_id)
