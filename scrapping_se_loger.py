import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from time import sleep
from selenium.common.exceptions import NoSuchElementException, TimeoutException,StaleElementReferenceException
import json
from mistral import Mistral


def scrapp_page(driver, num_page):
    print("Page number: ", num_page)
    loc_elements = driver.find_elements(By.XPATH, "//*[@data-testid='sl.explore.card-container']/a")
    sleep(2)
    logements = []
    i = 1
    for element in loc_elements:
        if 'bellesdemeures' in element.get_attribute("href") or 'seloger' not in element.get_attribute("href"):
            print('page skipped')
            continue
        element.click()  # on ouvre la page
        sleep(2)
        driver.switch_to.window(driver.window_handles[-1])  # driver switch de page

        sleep(2)
        try:
            test = driver.find_element(By.XPATH, "//*[contains(@class, 'sc-jsJBEP iXSECa')]")
            print(test.text)
        except NoSuchElementException:
            print("no element")
        # récupération d'informations

        try:
            info_logement = driver.find_element(By.XPATH,
                                                "//*[contains(@class, 'Summarystyled__ShowcaseSummaryContainer-sc-1u9xobv-0')]")
        except (NoSuchElementException, StaleElementReferenceException):
            info_logement = 'None'

        try:
            description_logement = driver.find_element(By.XPATH,
                                                       "//*[contains(@class, 'TitledDescription__TitledDescriptionContent-sc-p0zomi-1')]//p")
        except (NoSuchElementException, StaleElementReferenceException):
            description_logement = 'None'

        try:
            localisation = driver.find_element(By.XPATH, "//*[@data-test='localization-wrapper']")
        except (NoSuchElementException, StaleElementReferenceException):
            localisation = 'None'

        logements.append({'info_logement_' + str(i*27+num_page): info_logement.text,
                                           'description_logement_' + str(i+num_page*27): description_logement.text,
                                           'localisation_logement_' + str(i+num_page*27): localisation.text})
        i += 1
        # traitement par llm :

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        sleep(2)  # Attendre avant de passer au prochain élément
        print("logement " + str(i) + ' de la page : ' + num_page+  'done ...')
    print('Page number: ', num_page, ' done ...')
    return logements


def se_loger_scrapping(driver,nbr_pages):

    driver.get("https://google.com")
    sleep(2)
    '''accept_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='didomi-notice-agree-button']")))
    accept_button.click()'''

    logements = []
    for i in range(nbr_pages):
        logements.extend(scrapp_page(driver, i))
        driver.find_element(By.XPATH, "//*[@data-testid='gsl.uilib.Paging.nextButton']").click()
        sleep(2)

    return logements


def make_it_structured_with_mistral(logements):
    api_key = "YW76S25jxEUUlRqV7DHt2j10aOu676cR"
    client = Mistral(api_key=api_key)
    model = 'mistral-small-latest'

    # Initialisation du DataFrame avec les colonnes attendues
    df = pd.DataFrame(
        columns=["surface", "prix", 'localisation', "nombre_piece", 'meublé', "étage", 'piece', 'note_localisation',
                 'note_prix', 'note_équipement'])

    # Boucle sur chaque logement pour extraire les informations
    for logement in logements:
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system",
                 "content": "Tu es un expert immobilier. Tu reçois des annonces de logement à Paris et extraits les informations utiles."},
                {"role": "system",
                 "content": "Les informations à extraire doivent être dans le format suivant : ['surface', 'prix', 'localisation', 'nombre_piece', 'meublé', 'étage', 'piece', 'note_localisation', 'note_prix', 'note_équipement']."},
                {"role": "system",
                 "content": 'La surface est en m2, le prix en euro, la localisation en Paris, les notes sont sur une échelle de 1 à 5.'},
                {"role": "user", "content": logement}
            ]
        )
        extracted_data = response.choices[0].message.content.strip().split(",")
        if len(extracted_data) == len(df.columns):
            new_row = pd.DataFrame([extracted_data], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
    return df



if __name__ == "__main__":

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    #options.add_argument("--headless")  # Exécuter sans interface graphique
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-blink-features=AutomationControlled")  # Éviter la détection Selenium

    try:
        driver = webdriver.Chrome(options=options)
        Text = se_loger_scrapping(driver,10)
    except:
        driver = webdriver.Chrome(options=options)
        driver.quit()

        print("\nScrapper stopped, launching again in 4 seconds...")
        sleep(4)

        ## driver config
        driver = webdriver.Chrome(options=options)
        sleep(2)
        logements = se_loger_scrapping(driver, 10)

        filename = "logements.json"
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(logements, file, indent=4, ensure_ascii=False)

        print(f"Le fichier '{filename}' a été enregistré avec succès.")

