"""
skill_dictionary.py – Comprehensive IT skills dictionary with alias mapping.

Creates and persists a JSON file containing 200+ canonical skills, their
categories, and many aliases so that raw resume text can be normalised to a
consistent vocabulary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from config import SKILLS_DICT_PATH

# ────────────────────────────────────────────────────────────────────────────
# Skill Definitions:  canonical_name -> (category, [aliases])
# ────────────────────────────────────────────────────────────────────────────

_SKILLS_RAW: Dict[str, Tuple[str, List[str]]] = {
    # ── Programming Languages ────────────────────────────────────────────
    "Java": ("Programming Language", ["java", "java8", "java 8", "java11", "java 11", "java17", "jdk", "j2se", "core java"]),
    "Python": ("Programming Language", ["python", "python3", "python 3", "python2", "python 2", "py"]),
    "JavaScript": ("Programming Language", ["javascript", "js", "ecmascript", "es6", "es5", "es2015", "es2016", "es2017"]),
    "TypeScript": ("Programming Language", ["typescript", "ts"]),
    "C": ("Programming Language", ["c language", "c programming"]),
    "C++": ("Programming Language", ["c++", "cpp", "c plus plus"]),
    "C#": ("Programming Language", ["c#", "csharp", "c sharp"]),
    "Go": ("Programming Language", ["go", "golang"]),
    "Rust": ("Programming Language", ["rust", "rust-lang"]),
    "Ruby": ("Programming Language", ["ruby"]),
    "PHP": ("Programming Language", ["php", "php7", "php8"]),
    "Swift": ("Programming Language", ["swift"]),
    "Kotlin": ("Programming Language", ["kotlin"]),
    "Scala": ("Programming Language", ["scala"]),
    "R": ("Programming Language", ["r language", "r programming", "r-lang"]),
    "Perl": ("Programming Language", ["perl"]),
    "Shell Scripting": ("Programming Language", ["shell scripting", "bash", "shell script", "unix shell", "unix shell script", "unix shell scripting", "shell"]),
    "SQL": ("Programming Language", ["sql", "structured query language"]),
    "PL/SQL": ("Programming Language", ["pl/sql", "plsql", "pl sql"]),
    "T-SQL": ("Programming Language", ["t-sql", "tsql", "transact-sql", "transact sql"]),
    "Objective-C": ("Programming Language", ["objective-c", "objective c", "objc", "obj-c"]),
    "Groovy": ("Programming Language", ["groovy"]),
    "Dart": ("Programming Language", ["dart"]),
    "MATLAB": ("Programming Language", ["matlab"]),
    "SAS": ("Programming Language", ["sas"]),
    "COBOL": ("Programming Language", ["cobol"]),
    "Visual Basic": ("Programming Language", ["visual basic", "vb", "vb.net", "vba", "vbscript"]),
    "Assembly": ("Programming Language", ["assembly", "asm"]),
    "Lua": ("Programming Language", ["lua"]),
    "Haskell": ("Programming Language", ["haskell"]),
    "Clojure": ("Programming Language", ["clojure"]),
    "Erlang": ("Programming Language", ["erlang"]),
    "PowerShell": ("Programming Language", ["powershell", "ps1"]),

    # ── Web Frameworks / Libraries ───────────────────────────────────────
    "React": ("Framework", ["react", "react.js", "reactjs", "react js"]),
    "Angular": ("Framework", ["angular", "angular.js", "angularjs", "angular js", "angular 2", "angular2"]),
    "Vue.js": ("Framework", ["vue", "vue.js", "vuejs", "vue js"]),
    "Node.js": ("Framework", ["node.js", "nodejs", "node js", "node"]),
    "Express.js": ("Framework", ["express", "express.js", "expressjs"]),
    "Django": ("Framework", ["django"]),
    "Flask": ("Framework", ["flask"]),
    "FastAPI": ("Framework", ["fastapi", "fast api"]),
    "Spring": ("Framework", ["spring", "spring framework", "spring boot", "spring mvc", "spring aop", "spring security", "spring cloud", "spring batch"]),
    "Hibernate": ("Framework", ["hibernate"]),
    "Struts": ("Framework", ["struts", "struts2", "struts 2"]),
    "Ruby on Rails": ("Framework", ["ruby on rails", "rails", "ror"]),
    "ASP.NET": ("Framework", ["asp.net", "aspnet", "asp.net mvc", "asp.net core"]),
    ".NET": ("Framework", [".net", "dotnet", ".net core", ".net framework"]),
    "jQuery": ("Framework", ["jquery", "j query"]),
    "Bootstrap": ("Framework", ["bootstrap"]),
    "Tailwind CSS": ("Framework", ["tailwind", "tailwindcss", "tailwind css"]),
    "Next.js": ("Framework", ["next.js", "nextjs", "next js"]),
    "Nuxt.js": ("Framework", ["nuxt", "nuxt.js", "nuxtjs"]),
    "Svelte": ("Framework", ["svelte", "sveltekit"]),
    "Ember.js": ("Framework", ["ember", "ember.js", "emberjs"]),
    "Backbone.js": ("Framework", ["backbone", "backbone.js", "backbonejs"]),
    "Laravel": ("Framework", ["laravel"]),
    "Symfony": ("Framework", ["symfony"]),
    "JSP": ("Framework", ["jsp", "javaserver pages"]),
    "JSF": ("Framework", ["jsf", "javaserver faces"]),
    "EJB": ("Framework", ["ejb", "enterprise javabeans", "enterprise java beans"]),
    "JPA": ("Framework", ["jpa", "java persistence api"]),
    "JDBC": ("Framework", ["jdbc"]),
    "JMS": ("Framework", ["jms", "java message service"]),
    "Servlets": ("Framework", ["servlets", "servlet", "java servlet"]),

    # ── Databases ────────────────────────────────────────────────────────
    "Oracle": ("Database", ["oracle", "oracle db", "oracle database", "oracle 10g", "oracle 11g", "oracle 12c", "oracle 9i"]),
    "MySQL": ("Database", ["mysql", "my sql"]),
    "PostgreSQL": ("Database", ["postgresql", "postgres", "psql"]),
    "SQL Server": ("Database", ["sql server", "mssql", "ms sql", "microsoft sql server", "sql server 2008", "sql server 2012", "sql server 2016"]),
    "MongoDB": ("Database", ["mongodb", "mongo"]),
    "Redis": ("Database", ["redis"]),
    "Cassandra": ("Database", ["cassandra", "apache cassandra"]),
    "DynamoDB": ("Database", ["dynamodb", "dynamo db"]),
    "SQLite": ("Database", ["sqlite", "sqlite3"]),
    "DB2": ("Database", ["db2", "ibm db2"]),
    "MariaDB": ("Database", ["mariadb", "maria db"]),
    "Elasticsearch": ("Database", ["elasticsearch", "elastic search", "elastic"]),
    "Neo4j": ("Database", ["neo4j"]),
    "CouchDB": ("Database", ["couchdb", "couch db"]),
    "HBase": ("Database", ["hbase", "apache hbase"]),
    "Teradata": ("Database", ["teradata"]),
    "Snowflake": ("Database", ["snowflake"]),
    "Redshift": ("Database", ["redshift", "amazon redshift", "aws redshift"]),
    "BigQuery": ("Database", ["bigquery", "big query", "google bigquery"]),
    "Firebase": ("Database", ["firebase"]),
    "MS Access": ("Database", ["ms access", "microsoft access", "access"]),

    # ── Cloud Platforms ──────────────────────────────────────────────────
    "AWS": ("Cloud", ["aws", "amazon web services", "amazon aws"]),
    "Azure": ("Cloud", ["azure", "microsoft azure", "ms azure"]),
    "Google Cloud": ("Cloud", ["gcp", "google cloud", "google cloud platform"]),
    "Heroku": ("Cloud", ["heroku"]),
    "DigitalOcean": ("Cloud", ["digitalocean", "digital ocean"]),
    "IBM Cloud": ("Cloud", ["ibm cloud", "ibm bluemix", "bluemix"]),

    # ── Cloud Services ───────────────────────────────────────────────────
    "EC2": ("Cloud", ["ec2", "amazon ec2"]),
    "S3": ("Cloud", ["s3", "amazon s3"]),
    "Lambda": ("Cloud", ["lambda", "aws lambda"]),
    "CloudFormation": ("Cloud", ["cloudformation", "cloud formation"]),
    "SQS": ("Cloud", ["sqs", "amazon sqs"]),
    "SNS": ("Cloud", ["sns", "amazon sns"]),

    # ── DevOps / CI-CD ───────────────────────────────────────────────────
    "Docker": ("DevOps", ["docker"]),
    "Kubernetes": ("DevOps", ["kubernetes", "k8s"]),
    "Jenkins": ("DevOps", ["jenkins"]),
    "Ansible": ("DevOps", ["ansible"]),
    "Terraform": ("DevOps", ["terraform"]),
    "Chef": ("DevOps", ["chef"]),
    "Puppet": ("DevOps", ["puppet"]),
    "Vagrant": ("DevOps", ["vagrant"]),
    "CI/CD": ("DevOps", ["ci/cd", "cicd", "ci cd", "continuous integration", "continuous delivery", "continuous deployment"]),
    "CircleCI": ("DevOps", ["circleci", "circle ci"]),
    "Travis CI": ("DevOps", ["travis ci", "travisci", "travis"]),
    "GitHub Actions": ("DevOps", ["github actions"]),
    "GitLab CI": ("DevOps", ["gitlab ci", "gitlab-ci"]),
    "Bamboo": ("DevOps", ["bamboo"]),
    "Nagios": ("DevOps", ["nagios"]),
    "Prometheus": ("DevOps", ["prometheus"]),
    "Grafana": ("DevOps", ["grafana"]),
    "ELK Stack": ("DevOps", ["elk", "elk stack"]),
    "Splunk": ("DevOps", ["splunk"]),
    "New Relic": ("DevOps", ["new relic", "newrelic"]),

    # ── Version Control ──────────────────────────────────────────────────
    "Git": ("Version Control", ["git"]),
    "GitHub": ("Version Control", ["github"]),
    "GitLab": ("Version Control", ["gitlab"]),
    "Bitbucket": ("Version Control", ["bitbucket"]),
    "SVN": ("Version Control", ["svn", "subversion"]),
    "CVS": ("Version Control", ["cvs", "concurrent version system"]),
    "Perforce": ("Version Control", ["perforce", "p4"]),
    "TFS": ("Version Control", ["tfs", "team foundation server"]),
    "Mercurial": ("Version Control", ["mercurial", "hg"]),

    # ── Build / Package Tools ────────────────────────────────────────────
    "Maven": ("Build Tool", ["maven"]),
    "Gradle": ("Build Tool", ["gradle"]),
    "Ant": ("Build Tool", ["ant", "apache ant"]),
    "npm": ("Build Tool", ["npm"]),
    "Yarn": ("Build Tool", ["yarn"]),
    "Webpack": ("Build Tool", ["webpack"]),
    "pip": ("Build Tool", ["pip"]),
    "Make": ("Build Tool", ["make", "makefile"]),
    "CMake": ("Build Tool", ["cmake"]),

    # ── Testing ──────────────────────────────────────────────────────────
    "JUnit": ("Testing", ["junit"]),
    "Selenium": ("Testing", ["selenium", "selenium webdriver"]),
    "TestNG": ("Testing", ["testng"]),
    "Mockito": ("Testing", ["mockito"]),
    "Jest": ("Testing", ["jest"]),
    "Mocha": ("Testing", ["mocha"]),
    "Cypress": ("Testing", ["cypress"]),
    "PyTest": ("Testing", ["pytest"]),
    "Cucumber": ("Testing", ["cucumber"]),
    "JMeter": ("Testing", ["jmeter", "apache jmeter"]),
    "LoadRunner": ("Testing", ["loadrunner", "load runner"]),
    "SoapUI": ("Testing", ["soapui", "soap ui"]),
    "Postman": ("Testing", ["postman"]),

    # ── Data Engineering / ETL ───────────────────────────────────────────
    "Apache Spark": ("Data Engineering", ["spark", "apache spark", "pyspark"]),
    "Hadoop": ("Data Engineering", ["hadoop", "apache hadoop"]),
    "Hive": ("Data Engineering", ["hive", "apache hive"]),
    "Pig": ("Data Engineering", ["pig", "apache pig"]),
    "Kafka": ("Data Engineering", ["kafka", "apache kafka"]),
    "Airflow": ("Data Engineering", ["airflow", "apache airflow"]),
    "NiFi": ("Data Engineering", ["nifi", "apache nifi"]),
    "Informatica": ("Data Engineering", ["informatica"]),
    "Talend": ("Data Engineering", ["talend"]),
    "SSIS": ("Data Engineering", ["ssis", "sql server integration services"]),
    "SSRS": ("Data Engineering", ["ssrs", "sql server reporting services"]),
    "SSAS": ("Data Engineering", ["ssas", "sql server analysis services"]),
    "DataStage": ("Data Engineering", ["datastage", "data stage", "ibm datastage"]),
    "Ab Initio": ("Data Engineering", ["ab initio", "abinitio"]),
    "ETL": ("Data Engineering", ["etl", "extract transform load"]),
    "Data Warehousing": ("Data Engineering", ["data warehousing", "data warehouse", "dwh", "dw"]),
    "Data Modeling": ("Data Engineering", ["data modeling", "data modelling"]),
    "MapReduce": ("Data Engineering", ["mapreduce", "map reduce"]),

    # ── Business Intelligence ────────────────────────────────────────────
    "Tableau": ("BI", ["tableau"]),
    "Power BI": ("BI", ["power bi", "powerbi", "microsoft power bi"]),
    "QlikView": ("BI", ["qlikview", "qlik view"]),
    "Qlik Sense": ("BI", ["qlik sense", "qliksense"]),
    "Looker": ("BI", ["looker"]),
    "MicroStrategy": ("BI", ["microstrategy", "micro strategy"]),
    "Crystal Reports": ("BI", ["crystal reports"]),
    "Cognos": ("BI", ["cognos", "ibm cognos"]),
    "OBIEE": ("BI", ["obiee", "oracle bi"]),
    "SAS Visual Analytics": ("BI", ["sas visual analytics", "sas va"]),
    "SAP BusinessObjects": ("BI", ["sap businessobjects", "business objects", "businessobjects", "bobj"]),
    "Pentaho": ("BI", ["pentaho"]),

    # ── ML / AI ──────────────────────────────────────────────────────────
    "TensorFlow": ("ML/AI", ["tensorflow", "tf"]),
    "PyTorch": ("ML/AI", ["pytorch"]),
    "Keras": ("ML/AI", ["keras"]),
    "scikit-learn": ("ML/AI", ["scikit-learn", "sklearn", "scikit learn"]),
    "Machine Learning": ("ML/AI", ["machine learning", "ml"]),
    "Deep Learning": ("ML/AI", ["deep learning", "dl"]),
    "Natural Language Processing": ("ML/AI", ["natural language processing", "nlp"]),
    "Computer Vision": ("ML/AI", ["computer vision", "cv"]),
    "OpenCV": ("ML/AI", ["opencv"]),
    "NLTK": ("ML/AI", ["nltk"]),
    "spaCy": ("ML/AI", ["spacy"]),
    "Pandas": ("ML/AI", ["pandas"]),
    "NumPy": ("ML/AI", ["numpy"]),
    "SciPy": ("ML/AI", ["scipy"]),
    "Matplotlib": ("ML/AI", ["matplotlib"]),
    "Seaborn": ("ML/AI", ["seaborn"]),
    "XGBoost": ("ML/AI", ["xgboost"]),
    "LightGBM": ("ML/AI", ["lightgbm"]),
    "Hugging Face": ("ML/AI", ["hugging face", "huggingface", "transformers"]),
    "MLflow": ("ML/AI", ["mlflow"]),
    "Data Science": ("ML/AI", ["data science"]),

    # ── Web Technologies ─────────────────────────────────────────────────
    "HTML": ("Web Technology", ["html", "html5", "html 5"]),
    "CSS": ("Web Technology", ["css", "css3", "css 3"]),
    "XML": ("Web Technology", ["xml"]),
    "JSON": ("Web Technology", ["json"]),
    "AJAX": ("Web Technology", ["ajax"]),
    "REST": ("Web Technology", ["rest", "restful", "rest api", "restful api", "rest web services"]),
    "SOAP": ("Web Technology", ["soap", "soap api"]),
    "GraphQL": ("Web Technology", ["graphql"]),
    "WebSocket": ("Web Technology", ["websocket", "websockets"]),
    "XSLT": ("Web Technology", ["xslt", "xsl"]),
    "XSD": ("Web Technology", ["xsd"]),
    "WSDL": ("Web Technology", ["wsdl"]),
    "Web Services": ("Web Technology", ["web services"]),
    "Microservices": ("Web Technology", ["microservices", "micro services"]),
    "API Development": ("Web Technology", ["api development", "api design"]),
    "OAuth": ("Web Technology", ["oauth", "oauth2", "oauth 2.0"]),
    "JWT": ("Web Technology", ["jwt", "json web token"]),
    "SASS": ("Web Technology", ["sass", "scss"]),
    "LESS": ("Web Technology", ["less"]),

    # ── Mobile Development ───────────────────────────────────────────────
    "iOS": ("Mobile", ["ios"]),
    "Android": ("Mobile", ["android"]),
    "React Native": ("Mobile", ["react native"]),
    "Flutter": ("Mobile", ["flutter"]),
    "Xamarin": ("Mobile", ["xamarin"]),
    "Xcode": ("Mobile", ["xcode"]),
    "Cocoa Touch": ("Mobile", ["cocoa touch"]),
    "Core Data": ("Mobile", ["core data"]),

    # ── Operating Systems ────────────────────────────────────────────────
    "Linux": ("Operating System", ["linux", "ubuntu", "centos", "redhat", "red hat", "rhel", "debian", "fedora"]),
    "Unix": ("Operating System", ["unix"]),
    "Windows": ("Operating System", ["windows", "windows server", "windows xp", "win"]),
    "macOS": ("Operating System", ["macos", "mac os", "osx", "os x"]),

    # ── Servers / Middleware ──────────────────────────────────────────────
    "Apache Tomcat": ("Server", ["tomcat", "apache tomcat"]),
    "WebLogic": ("Server", ["weblogic", "oracle weblogic"]),
    "WebSphere": ("Server", ["websphere", "ibm websphere"]),
    "JBoss": ("Server", ["jboss", "wildfly"]),
    "Nginx": ("Server", ["nginx"]),
    "Apache HTTP": ("Server", ["apache http", "apache httpd", "apache web server"]),
    "IIS": ("Server", ["iis", "internet information services"]),
    "RabbitMQ": ("Server", ["rabbitmq", "rabbit mq"]),
    "ActiveMQ": ("Server", ["activemq", "active mq", "apache activemq"]),

    # ── Project Management / Methodology ─────────────────────────────────
    "Agile": ("Methodology", ["agile", "agile methodology"]),
    "Scrum": ("Methodology", ["scrum"]),
    "Kanban": ("Methodology", ["kanban"]),
    "Waterfall": ("Methodology", ["waterfall"]),
    "SAFe": ("Methodology", ["safe", "scaled agile"]),
    "Lean": ("Methodology", ["lean"]),
    "Six Sigma": ("Methodology", ["six sigma"]),
    "SDLC": ("Methodology", ["sdlc", "software development life cycle"]),
    "TDD": ("Methodology", ["tdd", "test driven development"]),
    "BDD": ("Methodology", ["bdd", "behavior driven development"]),
    "DevOps": ("Methodology", ["devops"]),

    # ── PM / Collaboration Tools ─────────────────────────────────────────
    "JIRA": ("Tool", ["jira"]),
    "Confluence": ("Tool", ["confluence"]),
    "Trello": ("Tool", ["trello"]),
    "Asana": ("Tool", ["asana"]),
    "Slack": ("Tool", ["slack"]),
    "Microsoft Teams": ("Tool", ["microsoft teams", "ms teams", "teams"]),
    "ServiceNow": ("Tool", ["servicenow", "service now"]),
    "Remedy": ("Tool", ["remedy", "bmc remedy"]),
    "SharePoint": ("Tool", ["sharepoint"]),
    "Visio": ("Tool", ["visio", "ms visio"]),
    "MS Office": ("Tool", ["ms office", "microsoft office"]),
    "MS Excel": ("Tool", ["ms excel", "excel", "microsoft excel"]),
    "MS Word": ("Tool", ["ms word", "microsoft word"]),
    "MS PowerPoint": ("Tool", ["ms powerpoint", "powerpoint", "microsoft powerpoint"]),
    "MS Project": ("Tool", ["ms project", "microsoft project"]),

    # ── IDE ───────────────────────────────────────────────────────────────
    "Eclipse": ("IDE", ["eclipse"]),
    "IntelliJ IDEA": ("IDE", ["intellij", "intellij idea"]),
    "Visual Studio": ("IDE", ["visual studio", "vs"]),
    "VS Code": ("IDE", ["vs code", "vscode", "visual studio code"]),
    "NetBeans": ("IDE", ["netbeans", "net beans"]),
    "PyCharm": ("IDE", ["pycharm"]),
    "RAD": ("IDE", ["rad", "rational application developer"]),
    "Android Studio": ("IDE", ["android studio"]),
    "Sublime Text": ("IDE", ["sublime", "sublime text"]),
    "Atom": ("IDE", ["atom"]),

    # ── Networking ───────────────────────────────────────────────────────
    "TCP/IP": ("Networking", ["tcp/ip", "tcp ip", "tcp"]),
    "DNS": ("Networking", ["dns"]),
    "DHCP": ("Networking", ["dhcp"]),
    "VPN": ("Networking", ["vpn"]),
    "Firewall": ("Networking", ["firewall"]),
    "Load Balancing": ("Networking", ["load balancing", "load balancer"]),
    "LAN/WAN": ("Networking", ["lan", "wan", "lan/wan"]),
    "Active Directory": ("Networking", ["active directory", "ad"]),
    "LDAP": ("Networking", ["ldap"]),
    "VMware": ("Networking", ["vmware"]),
    "Citrix": ("Networking", ["citrix"]),
    "Cisco": ("Networking", ["cisco"]),

    # ── Soft Skills ──────────────────────────────────────────────────────
    "Communication": ("Soft Skill", ["communication", "communication skills"]),
    "Teamwork": ("Soft Skill", ["teamwork", "team player", "team work"]),
    "Leadership": ("Soft Skill", ["leadership"]),
    "Problem Solving": ("Soft Skill", ["problem solving", "problem-solving"]),
    "Time Management": ("Soft Skill", ["time management"]),
    "Critical Thinking": ("Soft Skill", ["critical thinking"]),
    "Analytical Skills": ("Soft Skill", ["analytical skills", "analytical"]),
    "Project Management": ("Soft Skill", ["project management"]),
    "Stakeholder Management": ("Soft Skill", ["stakeholder management"]),
    "Requirements Gathering": ("Soft Skill", ["requirements gathering", "requirement gathering", "requirements analysis"]),
    "Business Analysis": ("Soft Skill", ["business analysis"]),
    "Documentation": ("Soft Skill", ["documentation"]),
    "Mentoring": ("Soft Skill", ["mentoring"]),
    "Presentation": ("Soft Skill", ["presentation", "presentation skills"]),
    "Negotiation": ("Soft Skill", ["negotiation"]),
    "Conflict Resolution": ("Soft Skill", ["conflict resolution"]),
    "Client Management": ("Soft Skill", ["client management"]),
    "Vendor Management": ("Soft Skill", ["vendor management"]),
    "Budget Management": ("Soft Skill", ["budget management"]),
    "Risk Management": ("Soft Skill", ["risk management"]),
    "Change Management": ("Soft Skill", ["change management"]),
    "Strategic Planning": ("Soft Skill", ["strategic planning"]),
    "Recruitment": ("Soft Skill", ["recruitment", "recruiting", "talent acquisition"]),
    "Sourcing": ("Soft Skill", ["sourcing", "candidate sourcing"]),
    "Interviewing": ("Soft Skill", ["interviewing"]),
    "Onboarding": ("Soft Skill", ["onboarding"]),
    "Performance Management": ("Soft Skill", ["performance management"]),
    "Employee Relations": ("Soft Skill", ["employee relations"]),

    # ── Misc / Protocols / Standards ─────────────────────────────────────
    "UML": ("Design", ["uml", "unified modeling language"]),
    "Design Patterns": ("Design", ["design patterns"]),
    "MVC": ("Design", ["mvc", "model view controller"]),
    "SOA": ("Design", ["soa", "service oriented architecture"]),
    "OOP": ("Design", ["oop", "object oriented programming", "oops"]),
    "OOAD": ("Design", ["ooad", "object oriented analysis and design"]),
    "Data Structures": ("Design", ["data structures"]),
    "Algorithms": ("Design", ["algorithms"]),
    "System Design": ("Design", ["system design"]),

    # ── Misc Tools ───────────────────────────────────────────────────────
    "Log4j": ("Tool", ["log4j"]),
    "SLF4J": ("Tool", ["slf4j"]),
    "TOAD": ("Tool", ["toad"]),
    "PuTTY": ("Tool", ["putty"]),
    "FileZilla": ("Tool", ["filezilla"]),
    "WinSCP": ("Tool", ["winscp"]),
    "Wireshark": ("Tool", ["wireshark"]),
    "Fiddler": ("Tool", ["fiddler"]),
    "SAP": ("Tool", ["sap"]),
    "Salesforce": ("Tool", ["salesforce"]),
    "PeopleSoft": ("Tool", ["peoplesoft"]),
    "Workday": ("Tool", ["workday"]),
    "ADP": ("Tool", ["adp"]),
    "Taleo": ("Tool", ["taleo"]),
    "iCIMS": ("Tool", ["icims"]),
    "LinkedIn Recruiter": ("Tool", ["linkedin recruiter"]),
    "BrassRing": ("Tool", ["brassring"]),
}


# ────────────────────────────────────────────────────────────────────────────
# Build derived structures
# ────────────────────────────────────────────────────────────────────────────

def build_dictionary() -> Dict:
    """Build the full dictionary structure ready for JSON serialisation."""
    skills: Dict[str, Dict] = {}
    alias_map: Dict[str, str] = {}  # lowercase alias -> canonical name

    for canonical, (category, aliases) in _SKILLS_RAW.items():
        skills[canonical] = {
            "category": category,
            "aliases": aliases,
        }
        # Map canonical name itself (lowered)
        alias_map[canonical.lower()] = canonical
        for alias in aliases:
            alias_map[alias.lower()] = canonical

    return {
        "skills": skills,
        "alias_map": alias_map,
        "categories": sorted({v[0] for v in _SKILLS_RAW.values()}),
    }


def save_dictionary(path: Optional[Path] = None) -> Path:
    """Build and persist the skill dictionary to JSON."""
    path = path or SKILLS_DICT_PATH
    data = build_dictionary()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return path


def load_dictionary(path: Optional[Path] = None) -> Dict:
    """Load the skill dictionary from disk."""
    path = path or SKILLS_DICT_PATH
    if not path.exists():
        save_dictionary(path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class SkillLookup:
    """Fast lookup wrapper around the skill dictionary.

    Supports O(1) alias resolution and regex-based extraction from free text.
    """

    def __init__(self, data: Optional[Dict] = None) -> None:
        if data is None:
            data = load_dictionary()
        self.skills: Dict[str, Dict] = data["skills"]
        self.alias_map: Dict[str, str] = data["alias_map"]
        self.categories: List[str] = data["categories"]

        # Build sorted aliases for longest-match-first regex
        sorted_aliases = sorted(self.alias_map.keys(), key=len, reverse=True)
        escaped = [re.escape(a) for a in sorted_aliases]
        self._pattern = re.compile(
            r"(?<![a-zA-Z])(" + "|".join(escaped) + r")(?![a-zA-Z])",
            re.IGNORECASE,
        )

    def resolve(self, raw_skill: str) -> Optional[str]:
        """Resolve a raw skill string to its canonical name."""
        return self.alias_map.get(raw_skill.lower().strip())

    def extract_from_text(self, text: str) -> Dict[str, int]:
        """Extract all skills mentioned in *text*, returning canonical names with counts."""
        hits: Dict[str, int] = {}
        for m in self._pattern.finditer(text):
            canonical = self.alias_map.get(m.group(0).lower())
            if canonical:
                hits[canonical] = hits.get(canonical, 0) + 1
        return hits

    def get_category(self, canonical: str) -> Optional[str]:
        """Return the category for a canonical skill name."""
        info = self.skills.get(canonical)
        return info["category"] if info else None

    @property
    def canonical_names(self) -> Set[str]:
        return set(self.skills.keys())


# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = save_dictionary()
    data = load_dictionary()
    print(f"Saved {len(data['skills'])} skills with {len(data['alias_map'])} aliases to {p}")
