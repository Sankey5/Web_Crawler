mv .envTemplate .env
sudo apt install python3-pip
sudo apt install python3-venv
python3 -m venv venv
sudo chmod u+x ./venv/bin/activate*
. ./venv/bin/activate
pip install -r linux_requirements.txt
