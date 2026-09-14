FROM python:3.10-slim

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and its system dependencies
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Expose Streamlit default port
EXPOSE 8501

# Run entrypoint script which starts both background scheduler and Streamlit dashboard
ENTRYPOINT ["/app/entrypoint.sh"]
