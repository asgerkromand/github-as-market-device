# 📄 Github as Market Device
**Authors:** Asger Balsby Kromand, Eva Iris Otto & Anders Blok

**Journal:** Consumption Markets & Culture

[**DOI:** [doi.org/xxxx](https://doi.org/xxxx)]

---
[TO_DO]
## 📚 Abstract
> [Abstract]

---

## 📂 Repository Structure
```
├── appendix/           # Datasets or download scripts
├── notebooks/          # Jupyter notebooks for scraping and analysis
├── outputs/            # Output files: datasets, plots and log
├── resources/          # Codebase - functions, scripts, and config.ini
├── results/            # Figures and tables from the paper
├── .python-version
├── CITATION.cff
├── github_terminology.txt  # Describing star, follow, follow
├── LICENSE
├── pyproject.toml      # Configuration file for uv environment
├── README.md           
├── requirements.txt    # Dependency file using pip
└── uv.lock             # Dependency file for using uv sync
```

---

## 🛠 Installation & Environment

In general we recommend using the package manager [uv](https://docs.astral.sh/uv/) for creating an uv virtual environment (venv) by using the uv.lock file.

For other environment options, we have also included a requirements.txt file, which in general can be combined with pip install using pip install -r requirements.txt.

### Step 1: Cloning the repository using git

Using your terminal, move to the desired location and run:

```bash
# Clone repository
git clone https://github.com/asgerkromand/github-as-market-device.git
cd github-as-market-device
```

### Step 2: Create the environment

#### **Option 1: Using pip**
```bash
# Create uv virtual environment from file
uv venv # Creates a fresh .venv in your working directory
source venv/bin/activate # On Windows: venv\Scripts\activate
uv sync # Installs dependencies into virtual environment
```

#### **Option 2: Using pip**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Required: Create additional files

#### **\texttt{config.ini}**
Create a configuration (config.ini) file at "resources/config.ini".

The config.ini file will contatin your github token, which you can generate by following this [guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

The config.file should be written as:
```bash
[github]
access_token = <your-token>
```

Be aware, that <your-token> must not be inclosed by ' or " in a config.ini file.

#### **\texttt{filepaths.py}**

To follow our example, we recommend creating a filepath system using the [pathlib](https://docs.python.org/3/library/pathlib.html) library. The file should be called filepaths.py and created at "resources/filepaths.py".

NB. For our filepaths, we created to sets, as the personal data had to be stored on a secure drive, where it was not feasible to put the codebase.

## ▶️ Usage

### Notebooks

The scraping, sorting, vizualising and analysis is performed in the notebooks, and the notebooks come in chronological order representing the pipeline for our paper. 

In the notebooks 1-5, the scraping and sorting of data happens. In notebook 6 the networks i visualized, and in notebook 7 the edges are explored more qualitatively. Lastly, the descriptive tables for both the analysis part and the additional tables for the appendix are produced.

**NB:** These notebooks represent the methodological pipeline use in our paper. Running them now, will *not* reproduce the original dataset used to produce the networks and tables in our paper.

*In order to run the pipeline, you need to manually input to files:* An initial company list (.csv) to input for the notebook "1. Collecting first-tier users.ipynb", and a second-tier company list (also .csv) as input for the notebook "2. Creating first-tier dataset.ipynb". For examples: See "output/second_tier_companies.csv" and "output/initial_list.csv".

### Generation of appendix

The appendix -- located at "appendix/appendix.pdf" -- is generated using Overleaf. You can [view the Overleaf document here](https://www.overleaf.com/read/xvghfbbjntbd#c8aed2).

The tables in the overleaf document are based on the data columns located in "appendix/appendix_files".

---

## 📌 Notes

### Note on reproducibility

The data files in this repository are not the original datasets used to produce the tables and networks presented in the paper. The original data was collected at an earlier stage, but running the code now would generate similar data using the same methodological steps, and is therefore reproducible in this sense. Some output files are dummy files included to protect personal data.

---

## 📜 Citation
If you use this code or data, please cite:

[TO-DO]

```bibtex
@article{lastname2025title,
  title={Title of the Paper},
  author={Last, First and Others},
  journal={Journal Name},
  year={2025},
  doi={10.xxxx/xxxxx}
}
```

---

## 📄 License

MIT License. For specification see file "LICENSE".

---

## 🙌 Acknowledgments

This paper is part of the [DISTRACT project](https://sodas.ku.dk/projects/distract/). DISTRACT is funded by an Advanced Grant from the European Research Council. Period: 1 January 2020 to 31 December 2024. 

Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Council Executive Agency. Neither the European Union nor the granting authority can be held responsible for them.

![image](https://erc.europa.eu/sites/default/files/inline-images/ERC%20logo.png)