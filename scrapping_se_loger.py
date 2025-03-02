import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from time import sleep
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, \
    ElementClickInterceptedException
import json
#from mistral import Mistral


def scrap_page(driver, num_page):
    '''
    Outil de scraping pour une seule page
    :param driver:
    :param num_page:
    :return:
    '''
    print("Page number: ", num_page)
    loc_elements = driver.find_elements(By.XPATH, "//*[@data-testid='sl.explore.card-container']/a")
    sleep(2)
    logements = []
    i = 1
    for element in loc_elements:
        if 'bellesdemeures' in element.get_attribute("href") or 'seloger' not in element.get_attribute("href"):
            print('page skipped')
            continue
        try :
            wait = WebDriverWait(driver, 10)
            element = wait.until(EC.element_to_be_clickable(element))
            element.click()  # on ouvre la page
            sleep(2)
        except NoSuchElementException:
            print('Page skipped because element not found')
            continue
        except ElementClickInterceptedException:
            print('Page skipped because element is intercepted by another element')
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue
        sleep(2)
        driver.switch_to.window(driver.window_handles[-1])  # driver switch de page

        sleep(2)
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
        #~ 27 elements par page
        logements.append({'info_logement_' + str(i+num_page*27): info_logement.text,
                                           'description_logement_' + str(i+num_page*27): description_logement.text,
                                           'localisation_logement_' + str(i+num_page*27): localisation.text})
        i += 1
        # traitement par llm :

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        sleep(2.5)  # Attendre avant de passer au prochain élément
        print(logements[-1])
        print("logement " + str(i) + ' de la page : ' + str(num_page)+  ' done ...')
    print('Page number: ', str(num_page), ' done ...')
    return logements




def se_loger_scraping(driver,nbr_pages_left, logements = [], nbr_iterations = 0): #logement = liste de logements avec toutes les info
    '''
    Version recursive, scrape page à page --
    :param driver:
    :param nbr_pages_left:
    :param logements:
    :param nbr_iterations: La premiere étant 0
    :return:>
    '''
    if nbr_pages_left == 0:
        return logements
    else :
        if nbr_iterations == 0:
            driver.get("https://www.seloger.com/immobilier/locations/immo-paris-75/bien-appartement/type-studio/")
        else :
            driver.get("https://www.seloger.com/immobilier/locations/immo-paris-75/bien-appartement/type-studio/?LISTING-LISTpg="+str(nbr_iterations+2))

        try :
            accept_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='didomi-notice-agree-button']"))
            )
            accept_button.click()

        except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
            print('pas de bouton "accepter", passe')

        logements.extend(scrap_page(driver, nbr_iterations))
    sleep(2)
    print('Passage à la page suivante ....... Encore {}.'.format(nbr_pages_left) + ' pages ) scraper')
    return se_loger_scraping(driver, nbr_pages_left -1, logements, nbr_iterations +1)





def make_it_structured_with_mistral(logements):
    api_key = ""
    client = Mistral(api_key=api_key)
    model = 'mistral-small-latest'

    df = pd.DataFrame(
        columns=["surface", "prix", 'localisation', "nombre_piece", 'meublé', "étage", 'piece', 'note_localisation',
                 'note_prix', 'note_équipement'])

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


    driver = webdriver.Chrome(options=options)
    logements = se_loger_scraping(driver,2)

    filename = "logements.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(logements, file, indent=4, ensure_ascii=False)

    print(f"Le fichier '{filename}' a été enregistré avec succès.")

