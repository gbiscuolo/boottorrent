Cases where BootTorrent may be useful would be:

* If the clients in your network are not getting enough bandwidth individually and have significant bandwidth being left unused, which causes increased boot times. With BootTorrent you can repurpose the remaining bandwidth to help clients mutually share it among themselves.

* If your server (such as a laptop) can only connect to your cluster of computers via a comparatively slow link (such as WiFi or Fast-ethernet) then BootTorrent can help you mitigate the low bandwidth issues of network link.

* If you have large number of computers at your disposal and you're simply looking to deploy any given system image(s) (that may have been hand-crafted according to your needs) as painlessly as possible. BootTorrent can help you deploy it in `three easy steps <https://boottorrent.readthedocs.io/en/latest/quickstart.html>`_ to the whole network.

* If your current network boot server is unable to meet your requirements and deliver much needed performance, consider giving BootTorrent a try. Its distributed architecture will reduce the dependence on server, which means improved boot performance.

For more details on use cases please refer to `Use cases list <https://boottorrent.readthedocs.io/en/latest/usecases.html>`_ and visit the `documentation <https://boottorrent.readthedocs.io/en/latest/index.html>`_.

We have data to back our claims. Check out the performance improvements here:

.. |img1| image:: http://sl-lab.it/dokuwiki/lib/exe/fetch.php/tesi:txmedia_paper.png
.. |img2| image:: http://sl-lab.it/dokuwiki/lib/exe/fetch.php/tesi:seed-ratio_paper.png
.. |img3| image:: http://sl-lab.it/dokuwiki/lib/exe/fetch.php/tesi:tempiboot_paper.png

+------+------+------+
||img1|||img2|||img3||
+------+------+------+

[Images & Data courtesy of SL-Lab: http://sl-lab.it/dokuwiki/lib/exe/fetch.php/tesi:tesi_bruschi.pdf]

The above images were created from tests done at the University of Milan (ITALY) during the development of the original_ "boottorrent" project.

.. _original: http://sl-lab.it/dokuwiki/doku.php/tesi:boottorrent_en
