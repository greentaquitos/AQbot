
import discord
import asyncio
import sqlite3
import string
import random
import traceback
import re

from exceptions import FeedbackError
import bothelp


class Bot():
	def __init__(self, debug=True):
		self.debug = debug
		self.confirming = None

		self.commands = [
			("lookup",self.lookup),
			("calcs",self.calcs),
			("calc",self.calc),
			("help",self.help)
		]

		self.AQ = {
			'0': 0, 
			'1': 1, 
			'2': 2, 
			'3': 3, 
			'4': 4, 
			'5': 5, 
			'6': 6, 
			'7': 7, 
			'8': 8, 
			'9': 9, 
			'A': 10, 
			'B': 11, 
			'C': 12, 
			'D': 13, 
			'E': 14, 
			'F': 15, 
			'G': 16, 
			'H': 17, 
			'I': 18, 
			'J': 19, 
			'K': 20, 
			'L': 21, 
			'M': 22, 
			'N': 23, 
			'O': 24, 
			'P': 25, 
			'Q': 26, 
			'R': 27, 
			'S': 28, 
			'T': 29, 
			'U': 30, 
			'V': 31, 
			'W': 32, 
			'X': 33, 
			'Y': 34, 
			'Z': 35
		}
		
		if not debug:
			self.setup_db()
			self.setup_discord()

	# PROPERTIES

	# SETUP

	def setup_db(self):
		con = self.db = sqlite3.connect("db.db")
		schema = {
			"queries (q_string text unique, saved_at int, aq int, sent_by int)",
			"messages (content text unique, saved_at int, aq int, sent_by int, msg_id int)",
			"words (word text unique, saved_at int, aq int, sent_by int)"
		}

		for t in schema:
			try:
				con.execute("CREATE TABLE IF NOT EXISTS "+t)
			except Exception as e:
				self.log("Error with SQL:\n"+t+"\n"+str(e))
				break

		con.commit()

	def setup_discord(self):
		intents = discord.Intents.default()
		intents.members = True
		self.client = discord.Client(intents=intents)

	def start_bot(self,token):
		self.client.run(token)

	# UTIL

	def log(self, m):
		print(m)

	def debug_log(self, m):
		if self.debug:
			self.log(m)

	# EVENTS

	async def on_ready(self):
		self.log('AQbot ready')

	async def on_message(self,m):
		if m.author.bot:
			return

		self.log('got a message: '+m.content)

		respondable = True

		try:
			if m.content.lower().startswith('aq '):
				await self.parse_command(m)
			elif m.content.startswith('Y') and self.confirming:
				await self.confirm(m)
			elif m.content.lower().startswith('n') and self.confirming:
				await self.deny(m)
			else:
				respondable = False

		except FeedbackError as e:
			await m.reply(f"Hold up: {e}", mention_author=False)

		except Exception as e:
			self.log(traceback.format_exc())
			await m.reply(f"ERROR: {e}", mention_author=False)

		if not respondable:
			try:
				self.save_message(m)
			except Exception as e:
				self.log(traceback.format_exc())


	# COMMAND PARSING

	async def parse_command(self,m):
		for command,method in self.commands:
			if m.content[3:].lower().startswith(command):
				await method(m)
				return

	async def confirm(self,m):
		if m.author.id != self.confirming[1]:
			return
		self.confirming[0]()
		self.confirming = None
		await m.reply("Okay, done!", mention_author=False)

	async def deny(self,m):
		if m.author.id != self.confirming[1]:
			return
		self.confirming = None
		await m.reply("Okay, nevermind!", mention_author=False)

	def cleanemojis(self, string):
	    return re.sub(r"<a?:([a-zA-Z0-9_-]{1,32}):[0-9]{17,21}>", r":\1:", string)

	def cleanContent(self, c):
		return self.cleanemojis(c).upper().strip()

	def wordify(self,c):
		#remove links + non-alphanumeric chars, then split
		return [re.sub(r'^[^a-zA-Z0-9_\'’]+|[^a-zA-Z0-9_\'’]+$','', w) for w in c.split()]

	# GEMATRIA CALCULATIONS

	def string_to_aq(self,s):
		n = 0
		for c in s:
			if c in self.AQ:
				n += self.AQ[c]
		return n

	# SAVING

	def save_query(self,s,aq,u):
		cursor = self.db.cursor()
		cursor.execute("INSERT OR REPLACE INTO queries (q_string, saved_at, aq, sent_by) VALUES (?,datetime('now'),?,?)", [s,aq,u])
		self.db.commit()
		cursor.close()

	def save_message(self,m):
		cursor = self.db.cursor()
		content = self.cleanContent(m.content)
		aq = self.string_to_aq(content)
		sent_by = m.author.id
		msg_id = m.id
		cursor.execute("INSERT OR REPLACE INTO messages (content, saved_at, aq, sent_by, msg_id) VALUES (?,datetime('now'),?,?,?)",[content,aq,sent_by,msg_id])
		
		s = self.wordify(content)
		if len(s) > 1:
			for w in s:
				aq = self.string_to_aq(w)
				cursor.execute("INSERT OR REPLACE INTO words (word, saved_at, aq, sent_by) VALUES (?, datetime('now'), ?, ?)",[w,aq,sent_by])
		
		self.db.commit()
		cursor.close()

	# GETTING

	def get_aqs(self, aq, content):
		cur = self.db.execute("SELECT q_string FROM queries WHERE aq = ? ORDER BY RANDOM() LIMIT 10", [aq])
		queries = [q[0] for q in cur.fetchall()]

		cur = self.db.execute("SELECT content FROM messages WHERE aq = ? ORDER BY RANDOM() LIMIT 10", [aq])
		messages = [m[0] for m in cur.fetchall()]
		
		cur = self.db.execute("SELECT word FROM words WHERE aq = ? ORDER BY RANDOM() LIMIT 10", [aq])
		words = [w[0] for w in cur.fetchall()]

		cur.close()

		items = sorted(list(set(queries + messages + words)), key=len)

		while sum(len(s)+3 for s in items) + len(content) + len(str(aq)) + 10 > 6000:
			items.pop()

		random.shuffle(items)

		return items


	# RESPONSE FORMATTING

	async def help(self,m):
		h_content = m.content[8:]		
		reply = bothelp.default

		await m.reply(reply, mention_author=False)

	# return the number of the given string
	async def calc(self,m,plural=False):
		tc = m.content[9:] if plural else m.content[8:]
		content = self.cleanContent(tc)
		aq = self.string_to_aq(content)

		items = self.get_aqs(aq, content)
		while content in items:
			items.remove(content)

		if len(items) < 1:
			items = "???"
		elif plural:
			items = " = ".join(items)
		else:
			items = items[0]

		response = content + " = AQ " + str(aq) + " = " + items

		self.save_query(content, aq, m.author.id)

		embed = discord.Embed(description=response)

		await m.reply(embed=embed, mention_author=False)

	async def calcs(self,m):
		await self.calc(m,True)

	async def lookup(self,m):
		tc = m.content[10:]
		if not tc.isnumeric():
			raise FeedbackError("`aq lookup` only takes numerals")

		items = self.get_aqs(int(tc), tc)

		if len(items) < 1:
			items = "???"
		else:
			items = " = ".join(items)

		response = "AQ "+tc+" = "+items

		embed = discord.Embed(description=response)

		await m.reply(embed=embed, mention_author=False)

