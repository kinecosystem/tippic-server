export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES # https://github.com/ansible/ansible/issues/32499
ansible-playbook playbooks/tippic-server-prod.yml -i tippic-server-prod-kin3, -e 'ansible_python_interpreter=/usr/bin/python3'

