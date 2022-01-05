import sqlite3
import random


# for char-by-char, 8-11 seems to be the fun range where actual prev. messages aren't given much
# 3-6 it makes up neat words without spamming a page at a time
# for word-by-word, between 2 and 3 seems like the sweet spot

# 8-11, '' OR 2-3, ' ': coherent posts
# 6, '', no messages: schizoposting

# maybe use 4 inside a word + fuzzy-match the results for word-grams of a similar order?
	# and/or fuzzy match the results to a higher-order character-gram?

# maybe build aq-based array, generate a phrase naively that meets a prescribed aq, then "smooth" it out
	# by swapping out same-valued words for ones with better average vectors to neighbors, weighting nearer vectors higher

# could try short_corpus again w/ o=6?

# add cap on building anything > 4k chars
# get a dictionary-like baseline with actual sentences

# 4: 350k dict, 1k queries, 20k words, 30k messages
# 11: 60-70k dict, 10k words, 1k queries, 30k messages ?

class Markov():
	def __init__(self, order=11, delimiter='', db=None):
		self.db = sqlite3.connect("db.db") if not db else db

		self.chain_order = order
		self.delimiter = delimiter

		self.corpus = []
		self.chains = {}
		self.starts = {}
		self.long_starts = {}
		self.add_corpus_from_messages()
		self.add_corpus_from_queries()
		self.add_corpus_from_words()
		self.add_corpus_from_dict()
		self.generate_chain(5,'')
		self.generate_chain(11,'')
		self.generate_chain()

	def generate_chain(self, order=None, delimiter=None, text=None):
		order = order if order else self.chain_order
		delimiter = delimiter if delimiter else self.delimiter
		text = text if text else self.corpus

		if (order,delimiter) in self.chains:
			print("Chain already generated.")
			return

		print("Generating markov chain...")

		chain = {}
		messages_processed = 0
		starts = []
		long_starts = []

		for message in text:
			words = message.split(delimiter) if delimiter else [i for i in message]
			
			if len(words) < order+1:
				continue
			
			for w, word in enumerate(words):
				if len(words) < w+order+1:
					break
				
				prefix = delimiter.join([words[w+i] for i in range(order)])
				suffix = words[w+order]

				if prefix in chain:
					chain[prefix].append(suffix)
				else:
					chain[prefix] = [suffix]
					if w == 0:
						starts.append(prefix)
						if len(message.split(' ')) > 1:
							long_starts.append(prefix)

			messages_processed += 1
			if messages_processed % 1000 == 0:
				print(f"{messages_processed} messages processed")

		self.chains[(order,delimiter)] = chain
		self.starts[(order,delimiter)] = starts
		self.long_starts[(order,delimiter)] = long_starts

		print("Finished generating markov chain.")


	def add_corpus_from_messages(self):
		cursor = self.db.execute("SELECT content FROM messages")
		self.corpus += [m[0] for m in cursor.fetchall()]
		cursor.close()


	def generate_message(self):
		message = prefix = random.choice(self.starts[(self.chain_order,self.delimiter)])
		chain = self.chains[(self.chain_order,self.delimiter)]
		while prefix in chain:
			suffix = random.choice(chain[prefix])
			message += self.delimiter+suffix
			old_prefix_part = prefix.split(self.delimiter)[1:] if self.delimiter else [i for i in prefix][1:]
			prefix = self.delimiter.join(old_prefix_part + [suffix])
		return message


	# later do this with a gradient of chains per short and long
	def generate_creative(self):
		message = long_prefix = random.choice(self.long_starts[(11,'')])
		short_prefix = long_prefix[-5:]
		
		long_chain = self.chains[(11,'')]
		short_chain = self.chains[(5,'')]
		
		while short_prefix in short_chain or long_prefix in long_chain:
			suffix_options = []
			if short_prefix in short_chain:
				if long_prefix not in long_chain or random.random() > 9:
					suffix_options += short_chain[short_prefix]
			if long_prefix in long_chain:
				suffix_options += long_chain[long_prefix]
			suffix = random.choice(suffix_options)
			message += suffix

			long_prefix = long_prefix[1:] + suffix
			short_prefix = short_prefix[1:] + suffix

		return message


	def add_corpus_from_queries(self):
		cursor = self.db.execute("SELECT q_string FROM queries")
		queries = [q[0] for q in cursor.fetchall() if len(q[0]) < 500]
		cursor.close()
		self.corpus += queries

	def add_corpus_from_words(self):
		cursor = self.db.execute("SELECT word FROM words")
		words = [w[0] for w in cursor.fetchall()if len(w[0]) < 100]
		cursor.close()
		self.corpus += words

	def add_corpus_from_dict(self):
		self.corpus += open("words.txt").read().upper().splitlines()