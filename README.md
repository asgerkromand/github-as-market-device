# Github as Market Device

To-do for repo:
    - README
        - Describe i readme:
			- Hvordan man downloader environment og sætter det op (uv env osv.)
			- config.ini med tokens
			- filepaths
			- At data med personlige oplysninger er dummy eksempler og lagret på sikre lokale dreve.
			- Beskrive firmaliste
			- Beskriv at repository indeholder test-filer output filer, da kodeprocessen har foregået over lang tid, og er blevet optimeret undervejs på en måde, der gør at de ikke længere er kompatible. De metodiske skridt er dog de samme, og koden ville kunne reproducere måden hvorpå data er blevet samlet ind.
    - Update citation.cff med date released og publist-data

# 📄 Github as Market Device
**Authors:** Asger Balsby Kromand, Eva Iris Otto & Anders Blok
**Journal/Conference:** Consumption Markets & Culture 
[**DOI:** [doi.org/xxxx](https://doi.org/xxxx)] 

---

## 📚 Abstract
> [Abstract]

---

## 📂 Repository Structure
```
├── appendix/           # Datasets or download scripts
├── notebooks/          # Jupyter notebooks for scraping and analysis
├── outputs/            # Output files: datasets, plots and log
├── results/            # Figures, tables, and outputs
├── resources/          # Codebase - functions, scripts, and config.ini
├── .python-version
├── CITATION.cff
├── github_terminology.txt  # Describing star, follow, follow
├── LICENSE
├── pyproject.toml      # Configuration file for uv environment
├── README.md           
├── requirements.txt    # Dependency file using pip freeze > requirements.txt
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

#### **config.ini**
Create a configuration (config.ini) file at "resources/config.ini".

The config.ini file will contatin your github token, which you can generate by following this [guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

The config.file should be written as:
```bash
[github]
access_token = <your-token>
```

Be aware, that the token must not be inclosed by ' or " in a config.ini file.

#### **filepaths.py**

To follow our example, we recommend creating a filepath system using the [pathlib](https://docs.python.org/3/library/pathlib.html) library. The file should be called filepaths.py and created at "resources/filepaths.py".

NB. For our filepaths, we created to sets, as the personal data had to be stored on a secure drive, where it was not feasible to put the codebase.

## ▶️ Usage

### Reproduce Experiments
```bash
python src/train.py --config configs/experiment.yaml
```

### Generate Figures
```bash
python src/plot_results.py
```

---

## 📊 Results
| Method         | Metric A | Metric B |
|----------------|----------|----------|
| Our Method     | 0.92     | 0.85     |
| Baseline       | 0.88     | 0.80     |

---

## 📜 Citation
If you use this code or data, please cite:
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
Specify your license, e.g., MIT, Apache 2.0, or CC-BY for data.

---

## 🙌 Acknowledgments
Funding sources, collaborations, or software you built upon.