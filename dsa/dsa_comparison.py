import time
import json

class TransactionSearch:
    """
    Compare Linear Search vs Dictionary Lookup for transaction records
    """
    
    def __init__(self, transactions):
        self.transactions_list = transactions
        self.transactions_dict = {t['id']: t for t in transactions}
    
    def linear_search(self, transaction_id):
        """
        Linear Search - O(n) time complexity
        Scan through list sequentially to find transaction by ID
        """
        for transaction in self.transactions_list:
            if transaction['id'] == transaction_id:
                return transaction
        return None
    
    def dictionary_lookup(self, transaction_id):
        """
        Dictionary Lookup - O(1) average time complexity
        Use hash table for constant-time lookup
        """
        return self.transactions_dict.get(transaction_id)
    
    def benchmark_search(self, search_id, iterations=1000):
        """
        Benchmark both search methods
        """
        # Linear Search timing
        start = time.perf_counter()
        for _ in range(iterations):
            self.linear_search(search_id)
        linear_time = time.perf_counter() - start
        
        # Dictionary Lookup timing
        start = time.perf_counter()
        for _ in range(iterations):
            self.dictionary_lookup(search_id)
        dict_time = time.perf_counter() - start
        
        return {
            'linear_search_time': linear_time,
            'dictionary_lookup_time': dict_time,
            'speedup_factor': linear_time / dict_time if dict_time > 0 else 0
        }
    
    def run_comparison(self, test_ids):
        """
        Run comparison across multiple transaction IDs
        """
        results = []
        
        print("=" * 70)
        print("DSA SEARCH COMPARISON: Linear Search vs Dictionary Lookup")
        print("=" * 70)
        print(f"Total transactions: {len(self.transactions_list)}")
        print(f"Test IDs: {test_ids}\n")
        
        for tid in test_ids:
            result = self.benchmark_search(tid)
            results.append({
                'transaction_id': tid,
                **result
            })
            
            print(f"Transaction ID: {tid}")
            print(f"  Linear Search:      {result['linear_search_time']:.6f} seconds")
            print(f"  Dictionary Lookup:  {result['dictionary_lookup_time']:.6f} seconds")
            print(f"  Speedup Factor:     {result['speedup_factor']:.2f}x faster")
            print()
        
        # Calculate averages
        avg_linear = sum(r['linear_search_time'] for r in results) / len(results)
        avg_dict = sum(r['dictionary_lookup_time'] for r in results) / len(results)
        avg_speedup = avg_linear / avg_dict if avg_dict > 0 else 0
        
        print("=" * 70)
        print("AVERAGE RESULTS:")
        print(f"  Linear Search:      {avg_linear:.6f} seconds")
        print(f"  Dictionary Lookup:  {avg_dict:.6f} seconds")
        print(f"  Average Speedup:    {avg_speedup:.2f}x faster")
        print("=" * 70)
        
        return results

def main():
    # Load transactions from JSON
    with open('transactions.json', 'r') as f:
        transactions = json.load(f)
    
    # Ensure we have at least 20 records
    if len(transactions) < 20:
        print("Warning: Less than 20 transactions available")
    
    # Initialize search comparison
    searcher = TransactionSearch(transactions)
    
    # Test with multiple IDs (testing at least 20 records)
    test_ids = list(range(1, min(21, len(transactions) + 1)))
    
    # Run comparison
    results = searcher.run_comparison(test_ids)
    
    # Save results
    with open('dsa_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✓ Results saved to dsa_results.json")
    
    # Analysis
    print("\nANALYSIS:")
    print("Why is dictionary lookup faster?")
    print("- Linear Search: O(n) - must check each element sequentially")
    print("- Dictionary Lookup: O(1) - uses hash table for direct access")
    print("\nOther efficient data structures:")
    print("- Binary Search Tree: O(log n) for sorted data")
    print("- Hash Table with chaining: O(1) average case")
    print("- Trie: O(m) where m is key length, good for string keys")

if __name__ == "__main__":
    main()