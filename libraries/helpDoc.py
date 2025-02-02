# coding: utf-8

import codecs
import os
import re
import shutil
import unzip

import minestar
import mstarpaths
from license import License

logger = minestar.initApp()


def getResourcePath(path, overrides=None):
    """Find a UFS resource."""
    import ufs
    ufsPath = mstarpaths.interpretVarOverride(var="UFS_PATH", override=overrides)
    if not ufsPath:
        return None
    root = ufs.getRoot(ufsPath)
    if not root:
        return None
    res = root.getSubdir("res")
    if not res:
        return None
    ufsFile = res.get(path)
    if not ufsFile:
        return None
    return ufsFile.getPhysicalFile()


class HelpIndexDoc:

    """Class handling index.html file generation."""

    def __init__(self, locale='en_US'):
        self.locale = locale

    def getText(self, products=[]):
        """Get the text of the index.html file for the locale."""
        return self.getTextWhenProducts(products) if products else self.getTextWhenNoProducts()

    def getTextWhenNoProducts(self):
        path = self.getIndexPathWhenNoProducts(locale=self.locale)
        if path is None:
            path = self.getIndexPathWhenNoProducts(locale='en_US')
            if path is None:
                raise RuntimeError("Cannot find help doc index.html file for locale '%s'." % self.locale)
        with codecs.open(path, encoding="utf-8") as f:
            try:
                return f.read()
            finally:
                f.close()

    def getIndexPathWhenNoProducts(self, locale):
        return getResourcePath("minestar/platform/help/%s/doc/no-products-index.html" % locale)

    def getTextWhenProducts(self, products):
        path = self.getIndexPathWhenProducts(locale=self.locale)
        if path is None:
            path = self.getIndexPathWhenProducts(locale='en_US')
            if path is None:
                raise RuntimeError("Cannot find help doc index.html file for locale '%s'." % self.locale)
        with codecs.open(path, encoding="utf-8") as f:
            text = f.read()
            return text.replace('<div id="products"/>', self.getProductsDivText(products))

    def getIndexPathWhenProducts(self, locale):
        return getResourcePath("minestar/platform/help/%s/doc/products-index.html" % locale)

    def getProductsDivText(self, products):
        html = '<div id="products">' + os.linesep
        for product in products:
            html += self.getProductText(product) + os.linesep
        html += '</div>' + os.linesep
        return html

    def getProductText(self, product):
        def paragraph(id, text):
            return '<p id="%s">%s</p>' % (id, text)
        def anchor(link, text):
            return '<a href="%s">%s</a>' % (link, text)
        a = anchor(link=product + "/Default.htm", text=product)
        return paragraph(id=product, text=a)


class HelpDocInstaller:

    def __init__(self, products=[], locale='en_US'):
        self.products = products
        self.locale = locale
        self.helpDocDir = mstarpaths.interpretPath("{MSTAR_HELP}/%s" % locale)

    def install(self):
        installed = self.installProducts()
        if len(installed) > 0:
            self.installIndex(installed)
            return True
        return False

    def installProducts(self):
        logger.info("Checking for products to install for locale '%s' ..." % self.locale)
        return [x for x in self.products if self.installProduct(x)]

    def installProduct(self, product):
        # Get the product zip file, if any.
        productZipFile = self.getProductZipFile(product)
        if productZipFile is None:
            return False

        # Remove the existing product directory, if required.
        productHelpDocDir = os.path.join(self.helpDocDir, product)
        if os.path.exists(productHelpDocDir):
            logger.info("Removing existing help document for product '%s' ..." % product)
            shutil.rmtree(productHelpDocDir)

        logger.info("Installing help document for product '%s' ..." % product)
        logger.info("  From: %s" % productZipFile)
        logger.info("  To  : %s" % self.helpDocDir)

        # Create the destination directory, if required.
        if not os.path.exists(self.helpDocDir):
            os.makedirs(self.helpDocDir)

        try:
            unzip.unzip(productZipFile, self.helpDocDir)
            return True
        except Exception as e:
            logger.warning("Failed to install help document for product '%s': '%s'" % (product, e))
            return False

    def installIndex(self, products=[]):
        """Install the index.html file for the installed products."""
        indexHtmlPath = self.getHelpIndexFile()

        # Create the parent directory, if required.
        if not os.path.exists(os.path.dirname(indexHtmlPath)):
            os.makedirs(os.path.dirname(indexHtmlPath))

        logger.info("Writing help index for locale '%s' ..." % self.locale)

        html = self.getHelpIndexText(products)
        with codecs.open(indexHtmlPath, "w", "utf-8") as f:
            try:
                f.write(html)
            finally:
                f.close()
        return True

    def getHelpIndexFile(self):
        return os.path.join(self.helpDocDir, "index.html")

    def getHelpIndexText(self, products):
        return HelpIndexDoc(locale=self.locale).getText(products)

    def getProductZipFile(self, product):
        # Check that language updates directory exists.
        languagesDir = mstarpaths.interpretPath("{MSTAR_UPDATES}/languages")
        if not os.path.exists(languagesDir):
            return None

        # Search for a zip file matching the product and language code.
        # Looking for files with form: $product_Help_Doc_$locale_*.zip
        # But need to watch out for  : Command_Help_Doc_en_US_123.zip
        #                       and  : Command_Help_Doc_en_123.zip

        regex = re.compile('^' + product + '_Help_Doc_' + self.locale + '_[0-9].+.zip')
        for filename in os.listdir(languagesDir):
            if regex.match(filename):
                return os.path.join(languagesDir, filename)

        # No files found.
        return None


def splitLocaleTag(localeTag):
    parts = localeTag.split("_")
    if len(parts) < 2:
        raise RuntimeError("Invalid locale: '%s'" % localeTag)
    # Only handling "$language_$country" for now, not "$language_$country_$dialect"
    return (parts[0], parts[1])


def createLocaleTag(languageCode, countryCode=None):
    return languageCode if not countryCode else "%s_%s" % (languageCode, countryCode)


class LocalesTool:

    def __init__(self, overrides=None):
        self._countryCodes = None
        self.overrides = overrides

    def getDefaultLocale(self, languageCode='en'):
        if languageCode in self.countryCodes:
            return createLocaleTag(languageCode, self.countryCodes[languageCode])
        return languageCode

    def getLocales(self, languageCode='en', countryCode=None):
        locales = []

        def appendLocaleTag(tag):
            if tag and tag not in locales:
                locales.append(tag)

        # If the language code is a locale tag (e.g. "en_US") then split
        # into language code and country code.
        if '_' in languageCode:
            localeTag = languageCode
            (languageCode, countryCode) = splitLocaleTag(localeTag)
            locales = self.getLocales(languageCode=languageCode, countryCode=countryCode)
            appendLocaleTag(localeTag)
            return locales

        # Get the configured country code, if required.
        if countryCode is None:
            countryCode = self.getDefaultCountryCode()

        # First locale: $language_$country
        if countryCode:
            appendLocaleTag(createLocaleTag(languageCode, countryCode))

        # Second locale: $language_$defaultCountryFor($language)
        defaultCountryCode = self.countryCodes.get(languageCode)
        if defaultCountryCode:
            appendLocaleTag(createLocaleTag(languageCode, defaultCountryCode))

        # Third locale: $language
        appendLocaleTag(languageCode)

        return locales

    @property
    def countryCodes(self):
        if self._countryCodes is None:
            self._countryCodes = self._loadCountryCodes()
        return self._countryCodes

    def _loadCountryCodes(self):
        countryCodes = {}
        config = self.getLocaleToolsConfig()
        if 'countryCode.defaults' in config:
            s = config.get('countryCode.defaults').strip()
            if s[0] == '{' and s[-1] == '}':
                s = s[1:-1].strip()
            for token in [x.strip() for x in s.split(",")]:
                (language, country) = token.split(":")
                countryCodes[language] = country
        return countryCodes

    def getLocaleToolsConfig(self):
        properties = {}
        path = self.getLocaleToolsConfigFile()
        if path is not None:
            with open(path) as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    (k, v) = line.split("=")
                    k = k.strip()
                    v = v.strip()
                    if k and v:
                        properties[k] = v
        return properties

    def getLocaleToolsConfigFile(self):
        return getResourcePath(path="com/mincom/util/general/LocaleToolsConfig.properties",
                               overrides=self.overrides)

    def getDefaultCountryCode(self):
        return mstarpaths.interpretVarOverride(var="_COUNTRY", override=self.overrides)

class HelpDoc:

    """Class handling help doc generation."""

    def __init__(self, languageCode):
        self.languageCode = languageCode
        self._products = None
        self._localesTool = None

    def installed(self):
        """Determines if help doc is installed for the language."""
        for locale in self.locales:
            indexHtml = mstarpaths.interpretPath("{MSTAR_HELP}/%s/index.html" % locale)
            if os.path.exists(indexHtml):
                return True
        return False

    def install(self):
        """Installs help doc for the language."""
        logger.info("Installing help documents for language '%s' ..." % self.languageCode)

        # Install the help documents for the preferred locale.
        for locale in self.locales:
            if self.installHelpDocuments(locale):
                return

        # No help documents found for any locale, so write index.html for the default locale.
        self.installHelpIndex(self.defaultLocale)

    @property
    def locales(self):
        return self.localesTool.getLocales(self.languageCode)

    @property
    def defaultLocale(self):
        return self.localesTool.getDefaultLocale(self.languageCode)

    def installHelpDocuments(self, locale='en_US'):
        return HelpDocInstaller(products=self.products, locale=locale).install()

    def installHelpIndex(self, locale='en_US'):
        HelpDocInstaller(locale=locale).installIndex()

    @property
    def localesTool(self):
        if self._localesTool is None:
            self._localesTool = LocalesTool()
        return self._localesTool

    @property
    def products(self):
        if self._products is None:
            self._products = self._loadProducts()
            logger.info("Licensed for products: %s" % self._products)
        return self._products

    def _loadProducts(self):
        try:
            license = self.getLicense()
            if license is not None:
                return license.productNames
        except Exception as e:
            logger.warning("Failed to load MineStar license file: %s" % e)
        # No license, or error loading license, so no products.
        return []

    def getLicense(self):
        licensePath = mstarpaths.interpretPath("{MSTAR_INSTALL}/minestar.lic")
        if not os.path.exists(licensePath):
            logger.warning("Could not find MineStar license file at '%s'." % licensePath)
            return None
        logger.info("Loading license file '%s' ..." % licensePath)
        return License(licensePath)
