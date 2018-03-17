all:

install:
	mkdir -p $(DESTDIR)/usr/share/shuttle/slaves/debian
	cp *.py $(DESTDIR)/usr/share/shuttle/slaves/debian
	cp *.conf $(DESTDIR)/usr/share/shuttle/slaves/debian
	cp -r tools $(DESTDIR)/usr/share/shuttle/slaves/debian
	install -Dm644 config/sudoer ${DESTDIR}/etc/sudoers.d/shuttle-slave
	mkdir -p ${DESTDIR}/lib/systemd/system
	cp *.service ${DESTDIR}/lib/systemd/system
