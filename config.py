from decouple import config

# Email configuration
EMAIL_BODY_TRUNCATION_LENGTH = config('EMAIL_BODY_TRUNCATION_LENGTH', default=1000, cast=int)
TRUNCATION_INDICATOR = config('TRUNCATION_INDICATOR', default='... [truncated]')

# Database configuration
DB_PATH = config('DB_PATH', default='taskeroo.db')

# Other configurations
KEYWORDS_PATH = config('KEYWORDS_PATH', default='email_keywords.json')

# You can add more configuration variables here as needed
MAX_FETCH_EMAILS = config('MAX_FETCH_EMAILS', default=25, cast=int)