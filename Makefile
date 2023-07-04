.PHONY: help default install uninstall

help: default


default:
	@echo "install                install saydone to sys"
	@echo "uninstall              uninstall saydone"
	@echo "start                  start saydone service"
	@echo "stop                   stop saydone service"

install:
	@systemctl stop saydone || :
	ln -f saydone.py /usr/bin/saydone
	ln -f saydone.service /usr/lib/systemd/system/saydone.service
	systemctl daemon-reload
	systemctl enable --now saydone.service
	cat rc >> ~/.bashrc

uninstall:
	@systemctl stop saydone || :
	rm -f /usr/bin/saydone
	rm -f /usr/lib/systemd/system/saydone.service
	systemctl daemon-reload
	rm -f /var/log/saydone*

start:
	systemctl start saydone

stop:
	systemctl stop saydone
