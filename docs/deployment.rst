Deploying StreetSign in Production
==================================

How to deploy a 'production-ready' StreetSign installation.

Dependencies
------------

First, install the Python headers (for compiling some extra modules),
ImageMagick (to generate thumbnails), make, and git (to download StreetSign).

On Debian/Ubuntu Server, this will be::

    sudo apt-get install python3-dev make imagemagick git

On CentOS/RHEL 8+, this is::

    sudo yum install python3-devel make ImageMagick git

Then install `uv <https://docs.astral.sh/uv/>`_, which ``setup.sh`` uses to
create the virtualenv and install Python dependencies::

    curl -LsSf https://astral.sh/uv/install.sh | sh

User/Group
----------

StreetSign, like every other service, should really run as its own user, for
security's sake::

    sudo useradd streetsign

Which will also create a new group for it.

Installation path
-----------------

Following the LSB, the best place for public-facing services to install their
data is ``/srv/``.  Create that directory and install StreetSign there::

    sudo mkdir /srv/streetsign
    sudo chown -R streetsign:streetsign /srv/streetsign

Actually Installing it
----------------------

Make sure ``uv`` and ``make`` are installed first (see Dependencies).

We'll use git to clone the latest version and set it up::

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

Test that everything is ready
-----------------------------

This step is optional, but probably a good idea.  While still running
as the streetsign user::

    ./run.py waitress

and then from a web browser, browse to the server's IP on port 5000.  If you
don't know the server's IP::

    ip -4 addr show

Note that servers often have a firewall (e.g. iptables, or similar) blocking port 5000.

Then ``exit`` from the streetsign user.

Configure StreetSign to start at boot
-------------------------------------

Unfortunately, this is different on practically every Linux distribution.

There are startup files in the StreetSign source, in the ``deployment`` folder.

systemd systems (Ubuntu 20.04+, CentOS/RHEL 8+, Debian 11+, etc)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On a systemd-based Linux distribution,
copy the ``deployment/systemd/streetsign.service`` file to ``/etc/systemd/system``,
edit it to make sure it's all correct for your system (which it should be, if you've followed
the above instructions)::

    sudo cp /srv/streetsign/deployment/systemd/streetsign.service /etc/systemd/system/

Then enable the service::

    sudo systemctl enable streetsign

Then start it up::

    sudo systemctl start streetsign

If it starts without errors, you're done.  To verify that it starts on
boot, feel free to reboot the server and see what happens.

Logs for StreetSign can be found with the usual systemd tools::

    journalctl -u streetsign.service

Getting StreetSign onto Port 80
--------------------------------

If StreetSign is going to be public-facing and you want it on the standard
HTTP port 80 or over HTTPS, it's best to run a reverse proxy in front of it.

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

Copy the basic StreetSign configuration file in::

    sudo cp /srv/streetsign/deployment/nginx/streetsign /etc/nginx/sites-available/

on CentOS, copy it to ``/etc/nginx/conf.d/streetsign.conf``::

    sudo cp /srv/streetsign/deployment/nginx/streetsign /etc/nginx/conf.d/streetsign.conf

Edit it with whatever settings you wish.

The supplied configuration sets ``X-Forwarded-For`` and ``X-Forwarded-Proto``.
StreetSign ignores those headers unless ``TRUSTED_PROXY_HOPS`` is set to the
number of proxies in front of it, so set ``TRUSTED_PROXY_HOPS = 1`` in
``config.py`` (or the environment) when using this configuration.

Enable it (Debian only)::

    sudo ln -s /etc/nginx/sites-available/streetsign /etc/nginx/sites-enabled/

If StreetSign is the only thing you use nginx for and you don't need the
default welcome page, disable it::

    sudo rm /etc/nginx/sites-enabled/default

Then restart nginx::

    sudo systemctl restart nginx

Docker
~~~~~~

Pre-built images are published to `GitHub Container Registry
<https://github.com/jamswat/streetsign/pkgs/container/streetsign>`_ on every
tagged release — no local build required:

.. code-block:: bash

    docker run -d --name streetsign -p 5000:5000 ghcr.io/jamswat/streetsign:1.5

Each release publishes several tags: the full version (``1.5.0``), the
minor line (``1.5``), the major line (``1``), and ``latest`` (the newest
release).  Use ``1.5`` to get patch updates within the 1.5 series, or a full
version such as ``1.5.0`` to pin exactly.

Or with docker-compose (pulls the image automatically):

.. code-block:: bash

    docker compose up -d

See the `README <https://github.com/jamswat/streetsign#docker>`_ for
Docker-specific configuration, volume mounts, and docker-compose usage.

CentOS notes (especially SELinux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CentOS often has SELinux installed and locked down.  You will probably need to
allow httpd to make outgoing connections.

Run the following commands as root.

First, install semanage::

    yum install policycoreutils-python

Then allow httpd outgoing network access (to the actual Python server)::

    /usr/sbin/setsebool httpd_can_network_connect 1

To make that permanent::

    /usr/sbin/setsebool -P httpd_can_network_connect 1
