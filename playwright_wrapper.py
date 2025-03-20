from step_type import StepType
from steps import Step


class PlaywrightWrapper:
    def __init__(self, headless: bool = True, verbose: bool = False):
        if verbose:
            print("PlaywrightWrapper init")


        self.headless = headless
        self.verbose = verbose
        
        import playwright.sync_api
        playwright_instance = playwright.sync_api.sync_playwright().start()

        self.browser = playwright_instance.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()

    def close(self):
        if self.verbose:
            print("PlaywrightWrapper close")
        self.page.close()
        self.browser.close()
