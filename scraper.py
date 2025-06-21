import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def fetch_data(company_number: str, start_date: str, end_date: str):
    driver = webdriver.Chrome()
    try:
        driver.get('https://inquiry.mohre.gov.ae/')

        # Step 1: Select "Enquiry for Job Offer" from dropdown
        svc_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'select2-js-example-basic-single-container'))
        )
        svc_box.click()
        option = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Enquiry for Job Offer')]"))
        )
        option.click()

        # Step 2: Fill company number
        comp_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'inputCompanyNo'))
        )
        comp_input.clear()
        comp_input.send_keys(company_number)

        # Step 3: Fill date range using JS to avoid readonly issues
        for field_id, date_val in [('txt_JobOffer_StartDate', start_date), ('txt_JobOffer_EndDate', end_date)]:
            date_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, field_id))
            )
            driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
                date_input, date_val
            )

        # Step 4: Solve captcha (copy span text to input)
        captcha_text = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'spanDisplayOtp'))
        ).text
        captcha_input = driver.find_element(By.ID, 'InputOTP')
        captcha_input.clear()
        captcha_input.send_keys(captcha_text)

        # Step 5: Click search using JS click
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'btnSearchServiceData'))
        )
        driver.execute_script("arguments[0].click();", search_btn)

        # Step 6: Wait for results
        WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table-striped tbody tr'))
        )

        # Step 7: Parse results
        rows = driver.find_elements(By.CSS_SELECTOR, 'table.table-striped tbody tr')
        results = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) >= 4:
                date_str = cells[1].text.strip()         # <-- NEW: extract date here (format: DD/MM/YYYY)
                reference_number = cells[2].text.strip()
                permit_type = cells[3].text.strip()
                results.append({
                    'Date': date_str,
                    'ReferenceNumber': reference_number,
                    'PermitType': permit_type
                })

        # Debug output
        print(f"[{company_number}] Found {len(results)} results")
        for r in results:
            print(r)

        return results

    finally:
        time.sleep(2)
        driver.quit()