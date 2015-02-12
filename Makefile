pkg_name = yeti-web
user = yeti-web
app_dir = /home/$(user)

clean:
	make -C debian clean

package:
	 dpkg-buildpackage -us -uc -b

.PHONY: clean package
