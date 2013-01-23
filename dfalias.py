#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import urlparse
import netrc

import mechanize
from lxml import etree

# override .netrc values (machine: admin.df.eu)
USERNAME = ""
PASSWORD = ""

# starting location
URL = "https://admin.df.eu/kunde/index.php5"


class Connection(object):
	def __init__(self, url, username, password):
		self.url = url
		self.username = username
		self.password = password
		self.accounts = None
		self.domains = None
		self.br = self.setup_browser()
		
	def setup_browser(self):
		br = mechanize.Browser()
		br.set_handle_equiv(True)
		br.set_handle_gzip(False)
		br.set_handle_redirect(True)
		br.set_handle_referer(True)
		br.set_handle_robots(False)

		# debug
		br.set_debug_http(False)
		br.set_debug_redirects(False)
		br.set_debug_responses(False)

		br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Ubuntu; ' + \
			'Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1')]
		
		return br
	
	def login(self):
		# open login page and login
		self.br.open(self.url)
		self.br.select_form(nr=0)
		self.br.form.set_all_readonly(False)
		self.br.form['login'] = self.username
		self.br.form['km_password'] = self.password
		res = self.br.submit()
		
		doc = etree.parse(res, etree.HTMLParser())
		
		# login successfull?
		unsuccessfull_login = doc. \
			xpath("//li[@class='mark_box mark_error']/text()")
		if unsuccessfull_login \
			and "Login fehlgeschlagen" in unsuccessfull_login[0]:
			print("username and or password wrong")
			raise SystemExit(1)

		# maintenance?
		maintenance = doc.xpath("//div[@class='househeader']/text()")
		if maintenance:
			print("df.eu befindet sich momentan im Wartungsmodus")
			raise SystemExit(1)
			
		self.retrieve_available_domains()
		
	def retrieve_available_domains(self):
		# the list of domains are available within the statistics area
		req = self.br.click_link(text="Statistiken anzeigen")
		res = self.br.open(req)
		
		doc = etree.parse(res, etree.HTMLParser())
		self.domains = doc.xpath("//table[@class=" + \
			"'fancy_table tab_list sdw_border hottrack']//td[1]/text()")
	
	def retrieve_accounts(self):
		# go to the table of email addresses and extract them
		req = self.br.click_link(text="E-Mail-Adressen / ManagedExchange")
		res = self.br.open(req)
		
		doc = etree.parse(res, etree.HTMLParser())
		accounts_doc = doc. \
			xpath("//table[@id='accountTable']//child::tr[@style='']")

		accounts = {}
		for account_doc in accounts_doc:
			account = account_doc.xpath("td[1]//td[2]/text()[1]")[0].strip()
			aliases = account_doc.xpath("td[1]//td[2]/small/text()")
			qs = urlparse.parse_qs(account_doc.xpath("td[13]//a[1]/@href")[0])
			account_data = {
				"aliases" : aliases,
				"dn" : qs['dn'][0],
				"eaid": qs['eaid'][0],
			}
			accounts[account] = account_data
			
		self.accounts = accounts
		
	def list_accounts(self, filter=""):
		for account, account_data in self.accounts.iteritems():
			if filter in account:
				print("\033[1m{}:\033[0m (dn={}, eaid={})". \
					format(account, account_data["dn"], account_data["eaid"]))
				for alias in account_data["aliases"]:
					print("  " + alias)
				print("")
				
	def is_account_existent(self, account):
		return account in self.accounts.keys()
				
	def is_alias_defined(self, alias, account=None):
		if account:
			return alias in self.accounts[account]["aliases"]
		else:
			# search in all accounts
			addresses = self.accounts.keys()
			for account_data in self.accounts.values():
				addresses.extend(account_data["aliases"])
			return alias in addresses
	
	def create_alias(self, alias, account):
		# safety checks
		if not self.is_account_existent(account):
			print("no such account")
			raise SystemExit(1)
		if self.is_alias_defined(alias):
			print("alias already defined")
			raise SystemExit(1)
		if not alias.split("@")[1] in self.domains:
			print("domain is not under df.eu management")
			raise SystemExit(1)
		
		# go to email editing
		path = self.br.geturl().split("?")[0]
		dn = self.accounts[account]["dn"]
		eaid = self.accounts[account]["eaid"]
		location = "{}?action=edit&dn={}&eaid={}".format(path, dn, eaid)
		self.br.open(location)
		
		# select and extend form
		self.br.select_form(name="layerSettings")
		self.br.form.set_all_readonly(False)
		self.br.form.new_control("text", "layer_storage", {"value":"on"})
		self.br.form.new_control("text", "layer_alias", {"value":"on"})
		domain = account.split("@")[1]
		self.br.form.new_control("text", "domain[]", {"value":domain})
		
		# add existing aliases
		for i, alias_ in enumerate(self.accounts[account]["aliases"]):
			key = "alias[{}]".format(i)
			self.br.form.new_control("text", key, {"value":alias_})
		
		# add new alias
		key = "alias[{}]".format(len(self.accounts[account]["aliases"]))
		self.br.form.new_control("text", key, {"value":alias})
		
		self.br.submit()
		
	def delete_alias(self, alias, account):
		# safety checks
		if not self.is_account_existent(account):
			print("no such account")
			raise SystemExit(1)
		if not self.is_alias_defined(alias, account):
			print("alias non-existent for account")
			raise SystemExit(1)
		
		# go to email editing
		path = self.br.geturl().split("?")[0]
		dn = self.accounts[account]["dn"]
		eaid = self.accounts[account]["eaid"]
		location = "{}?action=edit&dn={}&eaid={}".format(path, dn, eaid)
		self.br.open(location)
		
		# select and extend form
		self.br.select_form(name="layerSettings")
		self.br.form.set_all_readonly(False)
		self.br.form.new_control("text", "layer_storage", {"value":"on"})
		self.br.form.new_control("text", "layer_alias", {"value":"on"})
		domain = account.split("@")[1]
		self.br.form.new_control("text", "domain[]", {"value":domain})
		
		# remove alias
		self.accounts[account]["aliases"].remove(alias)
		
		# add remaining aliases 
		for i, alias_ in enumerate(self.accounts[account]["aliases"]):
			key = "alias[{}]".format(i)
			self.br.form.new_control("text", key, {"value":alias_})
		
		self.br.submit()


def password_from_netrc(machine):
	try:
		auth = netrc.netrc().authenticators(machine)
		if auth:
			return auth[0], auth[2]
		else:
			return None
	except IOError:
		return None


def main():
	parser = argparse.ArgumentParser(description="Manage df.eu email aliases")
	parser.add_argument("-l", "--list", \
		action='store_true', help="list aliases")
	parser.add_argument("-a", "--account", \
		help="operate on this account, optional when listing", \
		metavar='ACCOUNT', default="")
	parser.add_argument("-c", "--create", \
		help="create the alias on the specified account", metavar='ALIAS',)
	parser.add_argument("-d", "--delete", \
		help="delete the alias from the specified account", metavar='ALIAS')
	args = parser.parse_args()
	
	# obtains credentials from .netrc, if available
	# may be overriden by specifying USERNAME and PASSWORD
	if not USERNAME and not PASSWORD:
		try:
			username, password = password_from_netrc("admin.df.eu")
		except TypeError:
			print("no username/password given")
			raise SystemExit(1)
	else:
		username, password = USERNAME, PASSWORD
		
	c = Connection(URL, username, password)
	c.login()
	
	if args.list:
		c.retrieve_accounts()
		c.list_accounts(args.account)
	elif args.create:
		if not args.account:
			print("please specify an account")
			raise SystemExit(1)
		c.retrieve_accounts()
		c.create_alias(args.create, args.account)
		c.retrieve_accounts()
		if c.is_alias_defined(args.create):
			print("success")
		else:
			print("failure")
			raise SystemExit(1)
	elif args.delete:
		if not args.account:
			print("please specify an account")
			raise SystemExit(1)
		c.retrieve_accounts()
		c.delete_alias(args.delete, args.account)
		c.retrieve_accounts()
		if not c.is_alias_defined(args.create):
			print("success")
		else:
			print("failure")
			raise SystemExit(1)


if __name__ == '__main__':
	main()


