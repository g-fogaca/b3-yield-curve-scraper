#%% Importing packages
import pandas as pd
from time import sleep
from io import StringIO
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#%% Functions

# Function for formating numbers
def format_number(value):
    if pd.isna(value) or value == '0':
        return value
    value = str(value).replace('.', '').replace(',', '')
    if len(value) > 2:
        return value[:-2] + '.' + value[-2:]
    return value

# Function to extract tables
def extract_table(date):
    try:
        # Check and switch to iframe if needed
        iframes = browser.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            browser.switch_to.frame(iframes[0])
        
        # Wait for the input field and the button
        wait = WebDriverWait(browser, 30)
        data_input = wait.until(EC.presence_of_element_located((By.ID, "Data")))
        
        # Clear the input field and insert the date
        data_input.clear()
        data_input.send_keys(date)
        
        # Click the OK button
        ok_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.expand")))
        ok_button.click()
        
        sleep(1)  # Wait for the table to load
        
        # Try to extract the table
        try:
            table_element = wait.until(EC.presence_of_element_located((By.ID, "tb_principal1")))
            table_html = table_element.get_attribute('outerHTML')
            tables = pd.read_html(StringIO(table_html), decimal=',')
            df = tables[0]
            
            # Format numbers in columns 1 and 2
            for col in [1, 2]:
                if col < len(df.columns):
                    df.iloc[:, col] = df.iloc[:, col].apply(format_number)
            df = df.apply(pd.to_numeric, errors='ignore')
            
            return df
        
        except Exception as e:
            print(f"Error extracting table for date {date}: {e}")
            return pd.DataFrame()  # Return an empty DataFrame in case of error
        
    except Exception as e:
        print(f"Error processing date {date}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

#%% Preparation    
# Input
dates_raw = pd.read_csv("data/input.csv")["period"]
dates_formatted = pd.to_datetime(dates_raw).dt.strftime("%d/%m/%Y")

# Webdriver manager
service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service=service)

#%% Web Scraping
browser.get("https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/mercado-de-derivativos/precos-referenciais/taxas-referenciais-bm-fbovespa/")

sleep(5)

# List to store dataframes for each date
dataframes = []

# Process each date
for date in dates_formatted:
    df = extract_table(date)
    df['Date'] = date  # Add a column for the date
    dataframes.append(df)

browser.close()

# Combine all dataframes into one
df_raw = pd.concat(dataframes, ignore_index=True)

#%% Data wrangling

df_clean = df_raw.copy().set_axis(["maturity", "business_days", "days360", "date", "business_days_error", "days360_error"], axis=1)
df_clean['business_days'] = df_clean['business_days'].combine_first(df_clean['business_days_error'])
df_clean['days360'] = df_clean['days360'].combine_first(df_clean['days360_error'])
df_clean.drop(columns=['business_days_error', 'days360_error'], inplace=True)
df_clean['date'] = pd.to_datetime(df_clean['date'], format='%d/%m/%Y')
cols = ['date'] + [col for col in df_clean.columns if col != 'date']
df_clean = df_clean[cols]

# Save output
df_clean.to_csv("data/output.csv", index=False)