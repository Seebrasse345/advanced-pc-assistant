 
class Solution:

	def run(self, index1, index2):
		self.index1 = index1
		self.index2 = index2

		index_common_ancestor = None
		def builder(index):
			up = int(index/2)
			return up
		
		
		solved = False
		while solved == False:
			index1 = builder(index1)
			index2= builder(index2)
			if index1 == index2:
				solved= True
				index_common_ancestor = index1
			else:
				solved= False


		return index_common_ancestor

index = 12
index2 = 7

print(Solution().run(index, index2))

