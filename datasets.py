import logging
import os
import re
import subprocess
import sys
import warnings
from io import BytesIO
from zipfile import ZipFile

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm.auto import tqdm

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


from data_utils import clean_directory_path, load_dict, save_dict
# from skfin.dataset_dates import load_fomc_change_date
# from skfin.dataset_mappings import mapping_10X, symbol_dict

#import ssl
#ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_kf_dataframes(df, multi_df=False):
    """
    extract the annual and monthly dataframes from the csv file with specific formatting
    """
    idx = [-2] + list(np.where(df.notna().sum(axis=1) == 0)[0])
    if multi_df:
        cols = ["  Average Value Weighted Returns -- Monthly"] + list(
            df.loc[df.notna().sum(axis=1) == 0].index
        )
    returns_data = {"Annual": {}, "Monthly": {}}
    for i in range(len(idx)):
        if multi_df:
            c_ = (
                cols[i]
                .replace("-- Annual", "")
                .replace("-- Monthly", "")
                .strip()
                .replace("/", " ")
                .replace(" ", "_")
            )
        if i != len(idx) - 1:
            v = df.iloc[idx[i] + 2 : idx[i + 1] - 1].astype(float)
            v.index = v.index.str.strip()
            if len(v) != 0:
                if len(v.index[0]) == 6:
                    v.index = pd.to_datetime(v.index, format="%Y%m")
                    if multi_df:
                        returns_data["Monthly"][c_] = v
                    else:
                        returns_data["Monthly"] = v
                    continue
                if len(v.index[0]) == 4:
                    v.index = pd.to_datetime(v.index, format="%Y")
                    if multi_df:
                        returns_data["Annual"][c_] = v
                    else:
                        returns_data["Annual"] = v
    return returns_data


def load_kf_returns(
    filename="12_Industry_Portfolios", cache_dir="data", force_reload=False
):
    """
    industry returns from Ken French:
    https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
    """

    if filename == "12_Industry_Portfolios":
        skiprows, multi_df = 11, True
    if filename == "F-F_Research_Data_Factors":
        skiprows, multi_df = 3, False
    if filename == "F-F_Momentum_Factor":
        skiprows, multi_df = 13, False
    if filename == "F-F_Research_Data_Factors_daily":
        skiprows, multi_df = 4, False

    output_dir = clean_directory_path(cache_dir) / filename
    if (output_dir.is_dir()) & (~force_reload):
        logger.info(f"logging from cache directory: {output_dir}")
        returns_data = load_dict(output_dir)
    else:
        logger.info("loading from external source")
        path = (
            "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
            + filename
            + "_CSV.zip"
        )
        r = requests.get(path)
        files = ZipFile(BytesIO(r.content))

        df = pd.read_csv(files.open(filename + ".CSV"), skiprows=skiprows, index_col=0)
        if "daily" in filename:
            returns_data = {
                "Daily": df.iloc[:-1].pipe(
                    lambda x: x.set_index(pd.to_datetime(x.index))
                )
            }
        else:
            returns_data = clean_kf_dataframes(df, multi_df=multi_df)

        logger.info(f"saving in cache directory {output_dir}")
        save_dict(returns_data, output_dir)
    return returns_data


def load_buffets_data(cache_dir="data", force_reload=False):
    """
    data from Stephen Lihn: site: https://github.com/slihn
    """
    filename = clean_directory_path(cache_dir) / "ffdata_brk13f.parquet"

    if (filename.is_file()) & (~force_reload):
        logger.info(f"logging from cache directory: {filename}")
        df = pd.read_parquet(filename)

    else:
        logger.info("loading from external source")
        path = "https://github.com/slihn/buffetts_alpha_R/archive/master.zip"
        r = requests.get(path) #, verify=False)
        files = ZipFile(BytesIO(r.content))

        df = pd.read_csv(
            files.open("buffetts_alpha_R-master/ffdata_brk13f.csv"), index_col=0
        )
        df.index = pd.to_datetime(df.index, format="%m/%d/%Y")
        logger.info(f"saving in cache directory {filename}")
        df.to_parquet(filename)
    return df


def load_sklearn_stock_returns(cache_dir="data", force_reload=False):
    """
    data from scikit-learn
    """
    filename = clean_directory_path(cache_dir) / "sklearn_returns.parquet"
    if (filename.is_file()) & (~force_reload):
        logger.info(f"logging from cache directory: {filename}")
        df = pd.read_parquet(filename)

    else:
        logger.info("loading from external source")
        url = "https://raw.githubusercontent.com/scikit-learn/examples-data/master/financial-data"
        df = (
            pd.concat(
                {
                    c: pd.read_csv(f"{url}/{c}.csv", index_col=0, parse_dates=True)[
                        "close"
                    ].diff()
                    for c in symbol_dict.keys()
                },
                axis=1,
            )
            .asfreq("B")
            .iloc[1:]
        )

        logger.info(f"saving in cache directory {filename}")
        df.to_parquet(filename)
    return df


def get_fomc_urls(from_year=1999, switch_year=None):
    if switch_year is None:
        from datetime import datetime

        switch_year = datetime.now().year - 5
    calendar_url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    r = requests.get(calendar_url)
    soup = BeautifulSoup(r.text, "html.parser")
    contents = soup.find_all(
        "a", href=re.compile("^/newsevents/pressreleases/monetary\d{8}[ax].htm")
    )
    urls_ = [content.attrs["href"] for content in contents]

    for year in range(from_year, switch_year):
        yearly_contents = []
        fomc_yearly_url = (
            f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
        )
        r_year = requests.get(fomc_yearly_url)
        soup_yearly = BeautifulSoup(r_year.text, "html.parser")
        yearly_contents = soup_yearly.findAll("a", text="Statement")
        for yearly_content in yearly_contents:
            urls_.append(yearly_content.attrs["href"])

    urls = ["https://www.federalreserve.gov" + url for url in urls_]
    return urls


def sent_cleaner(s):
    return s.replace("\n", " ").replace("\r", " ").replace("\t", " ").strip()


def bs_cleaner(bs, html_tag_blocked=None):
    if html_tag_blocked is None:
        html_tag_blocked = [
            "style",
            "script",
            "[document]",
            "meta",
            "a",
            "span",
            "label",
            "strong",
            "button",
            "li",
            "h6",
            "font",
            "h1",
            "h2",
            "h3",
            "h5",
            "h4",
            "em",
            "body",
            "head",
            "sup",
        ]
    return [
        sent_cleaner(t)
        for t in bs.find_all(text=True)
        if (t.parent.name not in html_tag_blocked) & (len(sent_cleaner(t)) > 0)
    ]


regexp = re.compile(r"\s+", re.UNICODE)


def feature_extraction(corpus, sent_filters=None):
    if sent_filters is None:
        sent_filters = [
            "Board of Governors",
            "Federal Reserve System",
            "20th Street and Constitution Avenue N.W., Washington, DC 20551",
            "Federal Reserve Board - Federal Reserve issues FOMC statement",
            "For immediate release",
            "Federal Reserve Board - FOMC statement",
            "DO NOT REMOVE:  Wireless Generation",
            "For media inquiries",
            "or call 202-452-2955.",
            "Voting",
            "For release at",
            "For immediate release",
            "Last Update",
            "Last update",
        ]

    text = [
        " ".join(
            [
                regexp.sub(" ", s)
                for i, s in enumerate(c)
                if (i > 1) & np.all([q not in s for q in sent_filters])
            ]
        )
        for c in corpus
    ]

    release_date = [pd.to_datetime(c[1].replace("Release Date: ", "")) for c in corpus]
    last_update = [
        pd.to_datetime(
            [
                s.replace("Last update:", "").replace("Last Update:", "").strip()
                for s in c
                if "last update: " in s.lower()
            ][0]
        )
        for c in corpus
    ]
    voting = [" ".join([s for s in c if "Voting" in s]) for c in corpus]
    release_time = [
        " ".join(
            [s for s in c if ("For release at" in s) | ("For immediate release" in s)]
        )
        for c in corpus
    ]

    return pd.DataFrame(
        {
            "release_date": release_date,
            "last_update": last_update,
            "text": text,
            "voting": voting,
            "release_time": release_time,
        }
    )


def load_fomc_statements(
    add_url=True, cache_dir="data", force_reload=False, progress_bar=False, from_year=1999
):
    """
    https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    """
    filename = clean_directory_path(cache_dir) / "fomc_statements.parquet"
    if (filename.exists()) & (~force_reload):
        logger.info(f"logging from cache file: {filename}")
        statements = pd.read_parquet(filename)
    else:
        logger.info("loading from external source")
        urls = get_fomc_urls(from_year=from_year)
        if progress_bar:
            urls_ = tqdm(urls)
        else:
            urls_ = urls
        corpus = [
            bs_cleaner(BeautifulSoup(requests.get(url).text, "html.parser"))
            for url in urls_
        ]
        statements = feature_extraction(corpus).set_index("release_date")
        if add_url:
            statements = statements.assign(url=urls)
        statements = statements.sort_index()
        logger.info(f"saving cache file {filename}")
        statements.to_parquet(filename)
    return statements


def load_loughran_mcdonald_dictionary(cache_dir="data", force_reload=False):
    """
    Software Repository for Accounting and Finance by Bill McDonald
    https://sraf.nd.edu/loughranmcdonald-master-dictionary/
    """
    # Define the filename and directory path
    filename = clean_directory_path(cache_dir) / "Loughran-McDonald_MasterDictionary_1993-2023.csv"
    
    # Ensure the directory exists
    filename.parent.mkdir(parents=True, exist_ok=True)

    if filename.exists() and not force_reload:
        logger.info(f"Loading from cache file: {filename}")
    else:
        logger.info("Loading from external source")
        file_id = "1ptUgGVeeUGhCbaKL14Ri3Xi5xOKkPkUD"
        url = f"https://docs.google.com/uc?export=download&id={file_id}"
        
        # Use requests to download the file
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            logger.info("File downloaded successfully.")
        else:
            logger.error(f"Failed to download the file. Status code: {response.status_code}")
            raise Exception("Failed to download the file.")

    # Load the CSV file into a DataFrame
    return pd.read_csv(filename)


def load_10X_summaries(cache_dir="data", force_reload=False):
    """
    Software Repository for Accounting and Finance by Bill McDonald
    https://sraf.nd.edu/sec-edgar-data/
    """
    filename = (
        clean_directory_path(cache_dir)
        / "Loughran-McDonald_10X_Summaries_1993-2021.csv"
    )
    if (filename.is_file()) & (~force_reload):
        logger.info(f"logging from cache directory: {filename}")
    else:
        logger.info("loading from external source")
        id = "1CUzLRwQSZ4aUTfPB9EkRtZ48gPwbCOHA"
        url = f"https://docs.google.com/uc?export=download&confirm=t&id={id}"
        subprocess.run(f"wget -O '{filename}' '{url}'", shell=True, capture_output=True)

    df = pd.read_csv(filename).assign(
        date=lambda x: pd.to_datetime(x.FILING_DATE, format="%Y%m%d")
    )
    return df


def load_ag_features(cache_dir="data", sheet_name="Monthly", force_reload=False):
    """
    load features from Amit Goyal's website:
    https://sites.google.com/view/agoyal145
    """
    filename = clean_directory_path(cache_dir) / "PredictorData2021.xlsx"
    
    # Ensure the directory exists
    filename.parent.mkdir(parents=True, exist_ok=True)

    if filename.exists() and not force_reload:
        logger.info(f"Loading from cache file: {filename}")
    else:
        logger.info("Downloading from external source")
        file_id = "1OArfD2Wv9IvGoLkJ8JyoXS0YMQLDZfY2"
        url = f"https://docs.google.com/uc?export=download&id={file_id}"
        
        # Download the file using requests
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            logger.info("File downloaded successfully.")
        else:
            logger.error(f"Failed to download the file. Status code: {response.status_code}")
            raise Exception("Failed to download the file.")

    # Load the Excel file into a DataFrame and process it
    return (
        pd.read_excel(filename, sheet_name=sheet_name)
        .assign(date=lambda x: pd.to_datetime(x.yyyymm, format="%Y%m"))
        .set_index("date")
    )

# Added part for the project

import os
import requests
import pandas as pd
from urllib.parse import urlencode

def download_fred_data(start_date, end_date, filename="data/fred_data.csv", indicator_id="UNRATE", overwrite=False):
    """
    Télécharge les données de la FED à partir de l'URL FRED et les enregistre dans un fichier CSV.

    :param start_date: Date de début au format AAAA-MM-JJ (e.g., "1948-01-01").
    :param end_date: Date de fin au format AAAA-MM-JJ (e.g., "2024-10-01").
    :param filename: Chemin où le fichier CSV sera sauvegardé (par défaut : "data/fred_data.csv").
    :param indicator_id: ID de l'indicateur à télécharger (par défaut : "UNRATE").
    :param overwrite: Si True, remplace le fichier existant. Sinon, ne télécharge pas si le fichier existe.
    :return: Un DataFrame pandas contenant les données téléchargées.
    """
    # Créez le dossier "data" s'il n'existe pas
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Vérifiez si le fichier existe
    if os.path.exists(filename) and not overwrite:
        print(f"Le fichier existe déjà : {filename}. Utilisez overwrite=True pour le remplacer.")
    else:
        # Base de l'URL
        base_url = "https://fred.stlouisfed.org/graph/fredgraph.csv"

        # Paramètres de l'URL
        params = {
            "bgcolor": "%23e1e9f0",
            "chart_type": "line",
            "drp": "0",
            "fo": "open sans",
            "graph_bgcolor": "%23ffffff",
            "height": "450",
            "mode": "fred",
            "recession_bars": "on",
            "txtcolor": "%23444444",
            "ts": "12",
            "tts": "12",
            "width": "1320",
            "nt": "0",
            "thu": "0",
            "trc": "0",
            "show_legend": "yes",
            "show_axis_titles": "yes",
            "show_tooltip": "yes",
            "id": indicator_id,
            "scale": "left",
            "cosd": start_date,
            "coed": end_date,
            "line_color": "%234572a7",
            "link_values": "false",
            "line_style": "solid",
            "mark_type": "none",
            "mw": "3",
            "lw": "3",
            "ost": "-99999",
            "oet": "99999",
            "mma": "0",
            "fml": "a",
            "fq": "Monthly",
            "fam": "avg",
            "fgst": "lin",
            "fgsnd": "2020-02-01",
            "line_index": "1",
            "transformation": "lin",
            "vintage_date": "2024-12-06",
            "revision_date": "2024-12-06",
            "nd": "1948-01-01",
        }

        # Construisez l'URL complète
        url = f"{base_url}?{urlencode(params)}"

        # Téléchargez le fichier
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Fichier téléchargé et sauvegardé dans : {filename}")
        else:
            print(f"Erreur lors du téléchargement : {response.status_code} - {response.text}")
            return None

    # Charger le fichier CSV
    try:
        df = pd.read_csv(filename)
        print("DataFrame créé avec succès.")
        # Convert observation_date column to datetime
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        # Set observation_date as index
        df.set_index('observation_date', inplace=True)
        return df
    except Exception as e:
        print(f"Erreur lors du chargement du CSV : {e}")
        return None


