=========
Internals
=========

Host Package
------------

This component runs on the computer that will serve the DHCP requests and act as a seed for the client computers in the network. The software parses the configuration files in the environment and then renders the final configuration file for various components from the parsed values and the template configuration files present in the package's assets/tpls directory. These parsed configuration files are then written to the out/ directory inside the environment. The software also generates torrent metadata for all the folders present in the oss/ directory.

External components that run on the host include:

* **Transmission**
    | For every sub-directory in the oss/ directory, a torrent file is created with the help of transmission-create binary and placed in the environment's out/torrents directory.
    | Transmission-daemon acts as the seeder for all the torrents.

* **bsdtar**
    | Because client computers can unpack RAM disks in their early phase of boot, the torrents metadata is packed into a RAM disk on the host and is unpacked by the client computers on booting the Phase-1 Linux system.
    | bsdtar is programatically used to pack the client configuration and torrent metadata into a RAM disk.

* **Dnsmasq**
    | Dnsmasq provides both a DHCP server and a TFTP server.
    | The DHCP server capability is used to prepare the client computers to start downloading the Phase-1 Linux system and torrent metadata from the TFTP server.
    | The TFTP server serves the Phase-1 Linux system on the TFTP protocol widely used by most PXE implementations.

* **Hefur**
    | Both DHT and LPD are prone to slow start or may not work at all.
    | Hefur is a simple RAM-only torrent tracker which is used to accelerate the discovery of seeds/peers on the network.

The package also uses a few Python libraries, which are:

* **Click**
    | It is used to implement the CLI for BootTorrent.

* **PyYAML**
    | It is used to work with YAML files.

* **Jinja2**
    | It is a templating engine used to render final configuration files from template configuration files.

* **Requests**
    | It is a HTTP library and is used to interact with transmission-daemon process via it's HTTP API.

An overview of the BootTorrent starting process is as follows:

1. Parse environment configuration files.
2. Write configuration files for external components into out/ directory.
3. Generate and pack the torrent metadata.
4. Start the external components with final configuration settings.
5. Standby and serve requests as they come.

Client Package
--------------

This component (also called Phase-1 Linux system), which is downloaded via TFTP and runs on the client computers, is a 32-bit x86 OS and is based on SliTaz Linux distribution. Bitness of 32-bit was chosen to maximize compatibility with older hardware that may not be able to run 64-bit x86_64/AMD64 binaries.

The included packages are:

* **Aria2**
    | It is used to download the actual files from the torrent metadata.

* **Kexec-tools**
    | It is used to load any Linux based OS via kexec process.

* **Qemu-x86_64**
    | It is a hypervisor to run user provided non-Linux OS.

* **Xorg**
    | It is used to provide Graphical display capabilities needed by Qemu.

* **BootTorrent TUI**
    | It is used to either accept user input and/or read client configuration and programatically calls above tools as necessary.

An overview of client's process is as follows:

1. PXE on client requests DHCP address.
2. Client receives DHCP address + PXE configuration.
3. Client downloads and executes the PXE Linux loader.
4. Linux loader downloads and executes the Phase-1 Linux kernel and initrd(s).
5. TUI binary is launched by the init system.
6. OS to load is chosed either via user input or configuration.
7. Download of the OS is initiated and saved to RAM.
8. OS is loaded via appropriate method.

Host process at a glance
------------------------

The BootTorrent executable uses env's out/ directory as it's working directory. It is cleaned before every run to remove any stale/old data.

1. Parsing Boottorrent.yaml
    | Boottorrent.yaml is parsed via PyYAML Python library and stored internally by the program into 'config' variable.

2. Write configuration for Dnsmasq.
    | 'dnsmasq' section of 'config' and assets/tpls/dnsmasq.conf.tpl are send to Jinja2 to get final configuration file for Dnsmasq which is then written to env's out/dnsmasq/dnsmasq.conf file.
    | Files for Phase 1 Linux system are also copied to out/dnsmasq/ph1 directory.

3. Generation of torrents.
    | For all the OSs present in the boottorrent.display_oss field, torrent file for individual OS is generated via transmission-create binary and placed into env's out/torrents directory.
    | If Hefur is enabled, it is added as external tracker to the torrents generated.

4. Write configuration for the client TUI.
    | TUI configuration is composed of two YAML files. These two files are parsed on the client to either display a TUI or load an OS.
    | out/torrents/configs.yaml file stores the booting information for the OSs.
    | out/torrents/Boottorrent.yaml file is a copy of env's Boottorrent.yaml file.

5. Generation of initrd carrying the client configuration.
    | Client configuration is transferred to clients via an additional initrd during boot process.
    | SliTaz kernel can unpack 'newc' type of initrd file. So, the env's out/torrents directory (containing torrent metadata + TUI configuration) is packed into a 'newc' archive which is then mounted by the kernel on client during its boot process without any additional software.
    | This new initrd is placed at out/dnsmasq/ph1/torrents.gz location.

6. Write configuration for Transmission.
    | 'transmission' section of the 'config' and assets/tpls/transmission.json.tpl are send to Jinja2 to get final configuration file for Transmission which is then written to env's out/transmission/settings.json file.

At this point, configuration for these components is present in the out/ directory and these processes are ready to be launched.
Note: Hefur doesn't require configuration file and its CLI is simple. So, it's not written.

7. Launch external components on the host.
    | After the configuration(s) is written for components, they are launched and passed the path to their respective configuration.

8. Add generated torrents to Transmission.
    | Torrent metadata present in the out/torrents directory is then added to Transmission via it's Web API.

At this point:

* Dnsmasq is ready to serve any DHCP/TFTP requests.
* Transmission is seeding the torrents.
* Hefur tracker (if enabled) is ready to serve the clients.

So, BootTorrent goes standby and waits for requests to come.

Interactions at a glance
------------------------

Loading of PXE Linux loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a computer starts and PXE boot is enabled in it's BIOS, it will send a DHCP request to any DHCP server on the network and anticipate PXE booting information with the response.
The DHCP protocol provides methods to instruct clients to launch a predefined PXE binary when responding with DHCP requests. These methods are used to launch a PXELinux loader (assets/ph1/pxelinux.0) on clients to prepare for the launch of the Phase 1 Linux system. Dnsmasq is configured to utilize these methods.

Loading of Phase 1 Linux kernel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once PXELinux loader is running, it will download it's configuration file (pxelinux.cfg, which is static and doesn't passes via Jinja2) from the TFTP server and read the details on how to load the Phase 1 Linux system.
It will then download a total of 4 files (again via TFTP):

* bzImage
    | The Linux kernel

* rootfs.gz
    | SliTaz initrd containing all the drivers, programs, utilities ... etc

* diff.gz
    | Contains the changes we want over rootfs.gz which are then overlaid on rootfs.gz
    | Currently contains only BootTorrent TUI, replacing /sbin/getty binary for minimal changes to rootfs.gz

* torrents.gz
    | Contains the torrent metadata + the TUI configuration

Once these files are downloaded, the PXELinux loader loads the Kernel.

Loading of the TUI
~~~~~~~~~~~~~~~~~~

The init system on the SliTaz image then attempts to load /sbin/getty binary which launches the TUI on client.

The below diagram illustrates how the booting process on client takes place.

.. seqdiag::

    seqdiag {
        host.DHCP; client.PXE; host.TFTP; client.LL; client.Ph1; client.TUI;
        client.PXE -> host.DHCP [label = "Req. DHCP address"]
        client.PXE <- host.DHCP [label = "IP Addr + PXE Config"]
        client.PXE -> host.TFTP [label = "Req. PXE Linux loader binary"]
        client.PXE <- host.TFTP [label = "Linux loader binary"]
        client.PXE -> client.LL [label = "Start Linux loader", leftnote = "PXE exits"]
        client.LL -> host.TFTP [label = "Req Kernel + initrd(s)"]
        client.LL <- host.TFTP [label = "Kernel + initrd(s)"]
        client.LL -> client.Ph1 [label = "Execute Phase-1 Kernel", leftnote = "Linux loader exits"]
        client.Ph1 -> client.TUI [label = "Init launches TUI"]
    }
