Deploying Streetsign in Production
==================================

How to deploy a 'production-ready' streetsign installation.

Dependencies
------------

First you need to install the python headers (for compiling some extra modules),
imagemagick (to generate thumbnails), and pip for installing other python modules,
and git for downloading streetsign itself.

On Debian/Ubuntu Server, this will be::

    sudo apt-get install python3-pip python3-dev imagemagick git

On CentOS/RHEL 8+, this is::

    sudo yum install python3-devel python3-pip ImageMagick git

User/Group
----------

Streetsign, as every other service, should really run as it's own user, for
security's sake ::

    sudo useradd streetsign

Which will also create a new group for it.

Installation path
-----------------

As per the LSB, probably the best place for public facing services to install their
data is ``/srv/``.  So we should create that directory, and install streetsign there::

    sudo mkdir /srv/streetsign
    sudo chown -R streetsign:streetsign /srv/streetsign

Actually Installing it
----------------------

We'll use git to get the latest version, and set it up as normal::

    cd /srv/streetsign
    sudo su streetsign
    git clone https://github.com/jamswat/streetsign.git .
    ./setup.sh

Set a secret key
----------------

Before running in production you **must** set a unique, random ``SECRET_KEY``
— the server refuses to start in production mode while it is left at the
insecure default. Generate one::

    python3 -c "import uuid; print(uuid.uuid4())"

and set it either in ``config.py``::

    SECRET_KEY = 'the-value-you-just-generated'

or via the environment (e.g. in the systemd unit or a ``.env`` file)::

    export SECRET_KEY='the-value-you-just-generated'

``SECRET_KEY`` signs session cookies, so keep it secret and never commit it to
a repository. It is *not* used for password hashing, so you can rotate it
without affecting stored passwords.

Test it's all ready to go
-------------------------

This step is technically un-needed, but probably a good idea.  While still ``su``'d as
streetsign::

    ./run.py waitress

and then from a web browser, browse to that server's IP at port 5000.  If you don't know
the server IP::

    ifconfig |grep 'inet addr:'

Note that often servers may have a firewall (e.g. IPTables, or similar) blocking port 5000.

And then you can ``exit`` from the streetsign user.

Configure streetsign to start on system-boot
--------------------------------------------

Unfortunately, this is different on practically every linux distribution.

There are startup files in the streetsign source, in the ``deployment`` folder.

systemd systems (Ubuntu 16.04+, CentOS/RHEL 7+, Debian 8+, etc)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On a systemd-based Linux distribution,
copy the ``deployment/systemd/streetsign.service`` file to ``/etc/systemd/system``,
edit it to make sure it's all correct for your system (which it should be, if you've followed
the above instructions)::

    sudo cp /srv/streetsign/deployment/systemd/streetsign.service /etc/systemd/system/

And then tell enable the service::

    sudo systemctl enable streetsign

And then you can actually start it up::

    sudo systemctl start streetsign

If it's all running quite happily, then cool.  If you want to test that it does actually start on
boot, feel free to reboot the server and see what happens.

Logs for streetsign can then be found using the normal systemd logging utils::

    journalctl -u streetsign.service

Getting Streetsign on to Port 80
--------------------------------

If streetsign is going to be 'public facing', and so you want it to be running on the regular
HTTP port 80, or over HTTPS, then it's best to run a 'reverse proxy' in front of it.

In-process static file serving via WhiteNoise_ means nginx is not required
for serving static assets — requests for static files should simply be
proxied to the app alongside everything else. However, if you do serve
static files directly through nginx, ensure the ``expires`` and ``alias``
directives match your deployment paths.

nginx
~~~~~

Install nginx::

    sudo apt-get install nginx

Or on CentOS::

    yum install nginx

copy the basic streetsign configuration file in::

    sudo cp /srv/streetsign/deployment/nginx/streetsign /etc/nginx/sites-available/

on CentOS, it's to ``/etc/nginx/conf.d/streetsign.conf``::

    sudo cp /srv/streetsign/deployment/nginx/streetsign /etc/nginx/conf.d/streetsign.conf

Edit it with whatever settings you wish.

Enable it (Debian Only)::

    sudo ln -s /etc/nginx/sites-available/streetsign /etc/nginx/sites-enabled/

And if streetsign is the only thing you're using nginx for, and you don't need
the default welcome page, turn that off::

    sudo rm /etc/nginx/sites-enabled/default

And of course, restart nginx::

    sudo systemctl restart nginx

Docker
~~~~~~

Pre-built images are published to `GitHub Container Registry
<https://github.com/jamswat/streetsign/pkgs/container/streetsign>`_ on every
tagged release — no local build required:

.. code-block:: bash

    docker run -d --name streetsign -p 5000:5000 ghcr.io/jamswat/streetsign:1.1.0

Or with docker-compose (pulls the image automatically):

.. code-block:: bash

    docker compose up -d

See the `README <https://github.com/jamswat/streetsign#docker>`_ for
Docker-specific configuration, volume mounts, and docker-compose usage.

CentOS Notes: (Esp. SELinux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CentOS has SELinux installed often, and is locked down pretty hard.  You will probably need to allow the HTTPD
to make outgoing connections.

(All of the following commands are as root.)

First install semanage::

    yum install policycoreutils-python

Then open up HTTPD to have outgoing-network access (to the actual python server)::

    /usr/sbin/setsebool httpd_can_network_connect 1

And to make that permanent::

    /usr/sbin/setsebool -P httpd_can_network_connect 1
