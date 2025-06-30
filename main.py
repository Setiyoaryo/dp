import os
import csv
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    WebDriverException, StaleElementReferenceException, ElementNotInteractableException
)
from dotenv import load_dotenv
import traceback
from datetime import datetime
import sys
import signal
from pathlib import Path

def setup_logging():
    log_filename = f'automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / log_filename

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    return logging.getLogger(__name__)

logger = setup_logging()

try:
    load_dotenv()
    logger.info("Environment loaded")
except Exception as e:
    logger.error(f"Failed to load environment: {e}")
    sys.exit(1)

class Config:
    def __init__(self):
        self._validate_environment()

    def _validate_environment(self):
        required_vars = ['USERNAME', 'PASSWORD', 'LOGIN_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing environment variables: {missing_vars}")

    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    LOGIN_URL = os.getenv("LOGIN_URL")
    PROXY_SERVER = os.getenv("PROXY_SERVER")
    MASTER_DATA_FILE = os.getenv("MASTER_DATA_FILE", 'master_data_dp.csv')
    DAILY_INPUT_FILE = os.getenv("DAILY_INPUT_FILE", 'input_dp.txt')

    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "15"))
    SHORT_TIMEOUT = int(os.getenv("SHORT_TIMEOUT", "5"))
    LONG_TIMEOUT = int(os.getenv("LONG_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))
    DROPDOWN_RETRIES = int(os.getenv("DROPDOWN_RETRIES", "3"))

    SELECTORS = {
        'login_button': [
            "#App > div > div.col-lg-5.d-flex.align-items-center.justify-content-center > div > form > div.my-3 > button",
            "button[type='submit']",
            ".btn-primary"
        ],
        'configuring_menu': [
            "#sidebar > ul > li:nth-child(3) > ul > li:nth-child(1) > a",
            "a[href*='configuring']"
        ],
        'dp_menu': [
            "#menu_0_1 > ul > li:nth-child(4) > a",
            "a[href*='dp']"
        ],
        'city_input': [
            "#vs1__combobox > div.vs__selected-options > input",
            "[id*='vs1'] input",
            ".vs__search"
        ],
        'rk_input': [
            "#vs2__combobox > div.vs__selected-options > input",
            "[id*='vs2'] input"
        ],
        'dp_input': [
            "#vs3__combobox > div.vs__selected-options > input",
            "[id*='vs3'] input"
        ],
        'filter_button': [
            "#dp_comp > div > div > div:nth-child(9) > div > a.btn.btn-primary",
            ".btn-primary",
            "button[type='submit']"
        ],
        'data_row': [
            "#lists_dp > tbody > tr",
            "tbody tr"
        ],
        'result_dp_code_cell': [
            "#lists_dp > tbody > tr:first-child > td:nth-child(2)",
            "tbody tr:first-child td:nth-child(2)"
        ],
        'no_data_message': [
            "//td[contains(text(),'No data available in table')]",
            "//td[contains(text(),'No data')]",
            ".dataTables_empty"
        ],
        'create_ticket_icon': [
            "#lists_dp > tbody > tr:first-child > td:nth-child(9) > a.btn.btn-success.btn-action > i",
            "tbody tr:first-child .btn-success i",
            ".btn-success"
        ],
        'final_create_button': [
            "#dp_comp > div > div > div.v--modal-overlay.scrollable > div > div.v--modal-box.v--modal > div.modal-body.card.border-gradient-mask2 > div > div > div > div.row.justify-content-center > div > a",
            ".modal-body .btn-primary",
            ".v--modal .btn"
        ],
        'confirm_create_button': [
            "body > div.swal2-container.swal2-center.swal2-backdrop-show > div > div.swal2-actions > button.swal2-confirm.swal2-styled",
            ".swal2-confirm",
            ".swal2-styled"
        ],
        'loading_overlay': [
            "div.vld-background",
            ".loading",
            ".overlay"
        ],
        'username_input': [
            "/html/body/div[1]/div/div/div[1]/div[1]/div/form/div[1]/div/input",
            "input[type='text']",
            "input[name='username']",
            "#username"
        ],
        'password_input': [
            "/html/body/div[1]/div/div/div[1]/div[1]/div/form/div[2]/div/input",
            "input[type='password']",
            "input[name='password']",
            "#password"
        ]
    }

config = Config()

class WebDriverManager:
    def __init__(self):
        self.driver = None
        self.service = None

    def create_driver(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])

            if config.PROXY_SERVER:
                options.add_argument(f'--proxy-server={config.PROXY_SERVER}')

            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "media_stream": 2,
                    "geolocation": 2,
                    "popups": 2
                },
                "profile.managed_default_content_settings": {"images": 2},
                "profile.default_content_settings": {"popups": 2}
            }
            options.add_experimental_option("prefs", prefs)

            try:
                self.service = Service()
                self.driver = webdriver.Chrome(service=self.service, options=options)
            except Exception:
                self.driver = webdriver.Chrome(options=options)

            self.driver.implicitly_wait(2)
            self.driver.set_page_load_timeout(config.LONG_TIMEOUT)
            self.driver.set_script_timeout(config.DEFAULT_TIMEOUT)

            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)

            return self.driver

        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            self.cleanup()
            raise

    def cleanup(self):
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    try:
                        self.driver.close()
                    except:
                        pass
                finally:
                    self.driver = None

            if self.service:
                try:
                    self.service.stop()
                except:
                    pass
                finally:
                    self.service = None

        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

class ElementHelper:
    def __init__(self, driver):
        self.driver = driver

    def find_element_with_fallback(self, selectors, timeout=None):
        timeout = timeout or config.DEFAULT_TIMEOUT
        for selector in selectors if isinstance(selectors, list) else [selectors]:
            try:
                if selector.startswith('//') or selector.startswith('.//'):
                    by = By.XPATH
                else:
                    by = By.CSS_SELECTOR

                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
                return element
            except:
                continue
        return None

    def wait_for_element(self, selectors, timeout=None, clickable=True):
        timeout = timeout or config.DEFAULT_TIMEOUT
        if not isinstance(selectors, list):
            selectors = [selectors]

        for selector in selectors:
            try:
                if selector.startswith('//') or selector.startswith('.//'):
                    by = By.XPATH
                else:
                    by = By.CSS_SELECTOR

                if clickable:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                else:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((by, selector))
                    )

                if element.is_displayed() and element.is_enabled():
                    return element
            except:
                continue
        return None

    def safe_click(self, element_or_selectors, element_name="element", use_js=False, max_attempts=3):
        if isinstance(element_or_selectors, (list, str)):
            element = self.wait_for_element(element_or_selectors, clickable=True)
        else:
            element = element_or_selectors

        if not element:
            return False

        for attempt in range(max_attempts):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                    element
                )
                time.sleep(0.5)

                if use_js or attempt > 0:
                    self.driver.execute_script("arguments[0].click();", element)
                else:
                    try:
                        element.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", element)
                return True

            except StaleElementReferenceException:
                if isinstance(element_or_selectors, (list, str)):
                    element = self.wait_for_element(element_or_selectors, clickable=True)
                    if not element:
                        return False
                else:
                    return False
            except:
                time.sleep(1)

        return False

    def handle_vue_select_dropdown(self, input_selectors, value_to_select, max_retries=None):
        max_retries = max_retries or config.DROPDOWN_RETRIES

        for attempt in range(max_retries):
            try:
                input_field = self.wait_for_element(input_selectors, timeout=10)
                if not input_field:
                    continue

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    input_field
                )
                time.sleep(0.5)

                input_field.click()
                time.sleep(0.3)

                try:
                    input_field.clear()
                    time.sleep(0.2)
                    input_field.send_keys(Keys.CONTROL + "a")
                    time.sleep(0.1)
                    input_field.send_keys(Keys.DELETE)
                    time.sleep(0.2)
                except:
                    pass

                for char in value_to_select:
                    input_field.send_keys(char)
                    time.sleep(0.05)

                time.sleep(1.5)

                exact_match_xpath = f"//ul[contains(@class, 'vs__dropdown-menu')]//li[normalize-space()='{value_to_select}']"
                option = self.wait_for_element([exact_match_xpath], timeout=5)
                if option:
                    if self.safe_click(option, f"Option '{value_to_select}'"):
                        time.sleep(0.5)
                        return True

                contains_xpath = f"//ul[contains(@class, 'vs__dropdown-menu')]//li[contains(normalize-space(), '{value_to_select}')]"
                option = self.wait_for_element([contains_xpath], timeout=3)
                if option:
                    if self.safe_click(option, f"Option containing '{value_to_select}'"):
                        time.sleep(0.5)
                        return True

                try:
                    input_field.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.3)
                    input_field.send_keys(Keys.ENTER)
                    time.sleep(0.5)
                    return True
                except:
                    pass

                try:
                    input_field.send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except:
                    pass

            except Exception as e:
                try:
                    input_field = self.wait_for_element(input_selectors, timeout=3)
                    if input_field:
                        input_field.send_keys(Keys.ESCAPE)
                except:
                    pass
                time.sleep(1)

        return False

    def wait_for_page_load(self, timeout=None):
        timeout = timeout or config.DEFAULT_TIMEOUT
        try:
            for selector in config.SELECTORS['loading_overlay']:
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue

            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
            return True
        except:
            return False

class DataManager:
    @staticmethod
    def validate_file_exists(filename, file_type="file"):
        if not filename:
            raise ValueError(f"{file_type} filename cannot be empty")
        file_path = Path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"{file_type} not found: {filename}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {filename}")
        return file_path

    @staticmethod
    def load_master_data(filename=None):
        filename = filename or config.MASTER_DATA_FILE
        try:
            file_path = DataManager.validate_file_exists(filename, "Master data file")
            master_data = {}
            required_fields = ['Kode_DP', 'City', 'RK']

            with open(file_path, mode='r', newline='', encoding='utf-8-sig') as file:
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                try:
                    delimiter = sniffer.sniff(sample).delimiter
                except:
                    delimiter = ','

                reader = csv.DictReader(file, delimiter=delimiter)
                if not reader.fieldnames:
                    raise ValueError("CSV file appears to be empty or invalid")

                cleaned_fieldnames = [field.strip() for field in reader.fieldnames]
                missing_fields = [field for field in required_fields if field not in cleaned_fieldnames]
                if missing_fields:
                    raise ValueError(f"CSV must contain columns: {required_fields}. Missing: {missing_fields}")

                row_count = 0
                for row_num, row in enumerate(reader, start=2):
                    try:
                        kode_dp = row['Kode_DP'].strip() if row['Kode_DP'] else ''
                        city = row['City'].strip() if row['City'] else ''
                        rk = row['RK'].strip() if row['RK'] else ''

                        if not kode_dp or not city or not rk:
                            continue

                        master_data[kode_dp] = {
                            'City': city,
                            'RK': rk,
                            'row_number': row_num
                        }
                        row_count += 1
                    except:
                        continue

            if not master_data:
                raise ValueError("No valid data found in master data file")

            logger.info(f"Master data loaded: {len(master_data)} entries")
            return master_data

        except Exception as e:
            logger.error(f"Error loading master data: {e}")
            return None

    @staticmethod
    def read_daily_input(filename=None):
        filename = filename or config.DAILY_INPUT_FILE
        try:
            file_path = DataManager.validate_file_exists(filename, "Daily input file")
            kode_dp_list = []
            seen_codes = set()

            with open(file_path, mode='r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#') or line in seen_codes:
                        continue
                    seen_codes.add(line)
                    kode_dp_list.append(line)

            logger.info(f"Daily input loaded: {len(kode_dp_list)} items")
            return kode_dp_list

        except Exception as e:
            logger.error(f"Error reading daily input: {e}")
            return []

class AutomationBot:
    def __init__(self):
        self.driver_manager = WebDriverManager()
        self.driver = None
        self.helper = None
        self.processed_dps = set()  # Real-time tracking
        self.stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }

    def initialize(self):
        try:
            logger.info("Initializing bot...")
            self.driver = self.driver_manager.create_driver()
            if not self.driver:
                raise RuntimeError("Failed to create WebDriver")
            self.helper = ElementHelper(self.driver)
            self.stats['start_time'] = datetime.now()
            logger.info("Bot initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            self.cleanup()
            return False

    def cleanup(self):
        try:
            if self.stats['start_time'] and not self.stats['end_time']:
                self.stats['end_time'] = datetime.now()
            if self.driver_manager:
                self.driver_manager.cleanup()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def login(self):
        if not all([config.LOGIN_URL, config.USERNAME, config.PASSWORD]):
            logger.error("Missing login credentials")
            return False

        for attempt in range(3):
            try:
                logger.info(f"Login attempt {attempt + 1}")
                self.driver.get(config.LOGIN_URL)

                if not self.helper.wait_for_page_load(timeout=config.LONG_TIMEOUT):
                    continue

                username_field = self.helper.wait_for_element(config.SELECTORS['username_input'])
                if not username_field:
                    continue

                username_field.clear()
                time.sleep(0.2)
                username_field.send_keys(config.USERNAME)
                time.sleep(0.3)

                password_field = self.helper.wait_for_element(config.SELECTORS['password_input'])
                if not password_field:
                    continue

                password_field.clear()
                time.sleep(0.2)
                password_field.send_keys(config.PASSWORD)
                time.sleep(0.3)

                login_button = self.helper.wait_for_element(config.SELECTORS['login_button'])
                if not login_button:
                    continue

                if not self.helper.safe_click(login_button, "Login button", use_js=True):
                    continue

                try:
                    WebDriverWait(self.driver, config.LONG_TIMEOUT).until(
                        EC.presence_of_element_located((By.ID, "sidebar"))
                    )
                    logger.info("Login successful")
                    current_url = self.driver.current_url
                    if 'login' not in current_url.lower():
                        return True
                    else:
                        continue
                except:
                    continue

            except Exception as e:
                if attempt < 2:
                    time.sleep(config.RETRY_DELAY)
                continue

        logger.error("All login attempts failed")
        return False

    def navigate_to_dp_menu(self):
        try:
            configuring_menu = self.helper.wait_for_element(config.SELECTORS['configuring_menu'])
            if not configuring_menu or not self.helper.safe_click(configuring_menu, "Configuring menu", use_js=True):
                return False

            time.sleep(2)

            dp_menu = self.helper.wait_for_element(config.SELECTORS['dp_menu'])
            if not dp_menu or not self.helper.safe_click(dp_menu, "DP menu", use_js=True):
                return False

            if not self.helper.wait_for_page_load(timeout=config.LONG_TIMEOUT):
                logger.warning("DP page load timeout")

            city_input = self.helper.wait_for_element(config.SELECTORS['city_input'], timeout=5)
            if city_input:
                logger.info("Navigated to DP page")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False

    def validate_filter_result(self, expected_kode_dp, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                time.sleep(2)

                for no_data_selector in config.SELECTORS['no_data_message']:
                    try:
                        if no_data_selector.startswith('//'):
                            no_data_elem = self.driver.find_element(By.XPATH, no_data_selector)
                        else:
                            no_data_elem = self.driver.find_element(By.CSS_SELECTOR, no_data_selector)

                        if no_data_elem.is_displayed():
                            return False, "NO_DATA"
                    except:
                        continue

                result_cell = self.helper.wait_for_element(
                    config.SELECTORS['result_dp_code_cell'],
                    timeout=10,
                    clickable=False
                )

                if result_cell:
                    result_dp_text = result_cell.text.strip()
                    if result_dp_text == expected_kode_dp:
                        return True, "MATCH"
                    else:
                        return False, "MISMATCH"
                else:
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        continue

            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(1)

        return False, "VALIDATION_FAILED"

    def process_ticket_creation(self, city, rk, kode_dp_value):
        try:
            if not self.helper.handle_vue_select_dropdown(config.SELECTORS['city_input'], city):
                return False
            time.sleep(0.5)

            if not self.helper.handle_vue_select_dropdown(config.SELECTORS['rk_input'], rk):
                return False
            time.sleep(0.5)

            if not self.helper.handle_vue_select_dropdown(config.SELECTORS['dp_input'], kode_dp_value):
                return False
            time.sleep(1)

            filter_button = self.helper.wait_for_element(config.SELECTORS['filter_button'])
            if not filter_button:
                return False

            validation_passed = False
            for filter_attempt in range(3):
                if not self.helper.safe_click(filter_button, "Filter button", use_js=True):
                    continue

                self.helper.wait_for_page_load()
                validation_result, validation_status = self.validate_filter_result(kode_dp_value)

                if validation_status == "NO_DATA":
                    return False
                elif validation_status == "MATCH":
                    validation_passed = True
                    break
                elif validation_status == "MISMATCH":
                    time.sleep(1)
                    continue
                else:
                    time.sleep(1)
                    continue

            if not validation_passed:
                return False

            create_ticket_icon = self.helper.wait_for_element(config.SELECTORS['create_ticket_icon'])
            if not create_ticket_icon or not self.helper.safe_click(create_ticket_icon, "Create ticket icon", use_js=True):
                return False

            self.helper.wait_for_page_load()
            time.sleep(2)

            final_create_button = self.helper.wait_for_element(config.SELECTORS['final_create_button'])
            if not final_create_button or not self.helper.safe_click(final_create_button, "Final create button", use_js=True):
                return False

            time.sleep(1)

            confirm_button = self.helper.wait_for_element(config.SELECTORS['confirm_create_button'])
            if not confirm_button or not self.helper.safe_click(confirm_button, "Confirm button", use_js=True):
                return False

            time.sleep(3)
            return True

        except Exception as e:
            logger.error(f"Ticket creation error for '{kode_dp_value}': {e}")
            return False

    def handle_page_refresh_and_navigation(self):
        try:
            self.driver.refresh()
            time.sleep(config.RETRY_DELAY)
            self.helper.wait_for_page_load(timeout=config.LONG_TIMEOUT)
            return self.navigate_to_dp_menu()
        except Exception as e:
            logger.error(f"Error during refresh: {e}")
            return False

    def generate_final_report(self, total_items):
        try:
            self.stats['end_time'] = datetime.now()
            duration = self.stats['end_time'] - self.stats['start_time']

            logger.info("="*50)
            logger.info("AUTOMATION COMPLETE")
            logger.info("="*50)
            logger.info(f"Duration: {duration}")
            logger.info(f"Total: {total_items} | Success: {self.stats['successful']} | Failed: {self.stats['failed']} | Skipped: {self.stats['skipped']}")

            new_items = total_items - self.stats['skipped']
            if new_items > 0:
                success_rate = (self.stats['successful'] / new_items * 100)
                logger.info(f"Success rate: {success_rate:.1f}%")

            if duration.total_seconds() > 0:
                items_per_minute = (self.stats['successful'] / (duration.total_seconds() / 60))
                logger.info(f"Rate: {items_per_minute:.1f} items/min")

            logger.info("="*50)

        except Exception as e:
            logger.error(f"Error generating report: {e}")

    def run_automation(self):
        try:
            logger.info("STARTING DP AUTOMATION BY SETIYO_ARYO")

            master_data = DataManager.load_master_data()
            if not master_data:
                logger.error("Failed to load master data")
                return False

            kode_dp_list = DataManager.read_daily_input()
            if not kode_dp_list:
                logger.error("No input data found")
                return False

            if not self.login():
                logger.error("Login failed")
                return False

            if not self.navigate_to_dp_menu():
                logger.error("Navigation failed")
                return False

            # Reset processed tracking for new session
            self.processed_dps.clear()

            total_items = len(kode_dp_list)
            logger.info(f"Processing {total_items} items")

            for index, kode_dp_value in enumerate(kode_dp_list, 1):
                try:
                    # Check if already processed in current session
                    if kode_dp_value in self.processed_dps:
                        logger.info(f"[{index}/{total_items}] SKIP: {kode_dp_value} (processed)")
                        self.stats['skipped'] += 1
                        continue

                    if kode_dp_value not in master_data:
                        logger.warning(f"[{index}/{total_items}] SKIP: {kode_dp_value} (not in master)")
                        self.stats['skipped'] += 1
                        continue

                    data = master_data[kode_dp_value]
                    city = data['City']
                    rk = data['RK']

                    logger.info(f"[{index}/{total_items}] Processing: {kode_dp_value}")

                    success = False
                    for attempt in range(config.MAX_RETRIES):
                        try:
                            if self.process_ticket_creation(city, rk, kode_dp_value):
                                success = True
                                break
                            else:
                                if attempt < config.MAX_RETRIES - 1:
                                    logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                                    if not self.handle_page_refresh_and_navigation():
                                        break
                                    time.sleep(config.RETRY_DELAY)
                        except Exception as e:
                            logger.error(f"Attempt {attempt + 1} error: {str(e)[:50]}")
                            if attempt < config.MAX_RETRIES - 1:
                                time.sleep(config.RETRY_DELAY)

                    if success:
                        self.processed_dps.add(kode_dp_value)
                        self.stats['successful'] += 1
                        logger.info(f"SUCCESS: {kode_dp_value}")
                    else:
                        self.stats['failed'] += 1
                        logger.error(f"FAILED: {kode_dp_value}")

                    # Brief pause between items
                    time.sleep(1)

                except KeyboardInterrupt:
                    logger.info("Process interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error processing {kode_dp_value}: {str(e)[:50]}")
                    self.stats['failed'] += 1

            self.generate_final_report(total_items)
            return True

        except Exception as e:
            logger.error(f"Automation error: {e}")
            return False
        finally:
            self.cleanup()

class ProcessTracker:
    """Real-time session tracking without persistent logs"""
    def __init__(self):
        self.session_start = datetime.now()
        self.processed_items = set()

    def is_processed(self, item):
        return item in self.processed_items

    def mark_processed(self, item):
        self.processed_items.add(item)

    def get_session_stats(self):
        return {
            'session_duration': datetime.now() - self.session_start,
            'processed_count': len(self.processed_items),
            'processed_items': list(self.processed_items)
        }

def signal_handler(signum, frame):
    logger.info("Received interrupt signal, cleaning up...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("DP Automation Bot Starting")

    bot = AutomationBot()
    try:
        if not bot.initialize():
            logger.error("Initialization failed")
            return False

        return bot.run_automation()

    except KeyboardInterrupt:
        logger.info("Process interrupted")
        return False
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        return False
    finally:
        bot.cleanup()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
