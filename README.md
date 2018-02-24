# Flair Polyglot V2 Node Server

![Build Status](https://travis-ci.org/therealmysteryman/udi-flair-polyglot.svg?branch=master)

This Poly provides an interface between Milight iBox 1 or 2 and Polyglot v2 server. Has been testing with RBGW Strip and MR16 bulb and  designed to work with the V6 protocol only. http://www.limitlessled.com/dev/

#### Installation

Installation instructions

You can install from Polyglot V2 store or manually : 

1. cd ~/.polyglot/nodeservers
2. git clone https://github.com/therealmysteryman/udi-flair-polyglot.git
3. run ./install.sh to install the required dependency.
4. Add a custom variable named host containing the IP Address of the Milight iBox ( eg : host 172.16.1.40 )
    You can add more then one iBox by seperating ip by comma (172.16.1.40,172.16.1.41).
.
#### Source

1. Based on the Node Server Template - https://github.com/Einstein42/udi-poly-template-python
