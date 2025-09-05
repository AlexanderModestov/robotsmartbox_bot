import asyncio
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from .models import User

class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            response = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        try:
            existing_user = await self.get_user_by_telegram_id(user_data['telegram_id'])
            
            if existing_user:
                response = self.client.table('users').update(user_data).eq('telegram_id', user_data['telegram_id']).execute()
            else:
                response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None
    
    async def search_automations_by_similarity(self, query_embedding: List[float], limit: int = 3, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search for similar automation documents using vector similarity
        
        Args:
            query_embedding: Query vector embedding from OpenAI (3072 dimensions)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of automation documents ranked by vector similarity
        """
        try:
            print(f"🔍 Searching for similar automations with threshold={threshold}, limit={limit}")
            
            # Get all documents with embeddings from the current automation database
            # Let's try without the null filter first to see what we get
            response = self.client.table('documents').select('''
                id, url, short_description, description, filename,
                embedding,
                automations!inner(
                    categories!inner(name)
                )
            ''').execute()
            
            print(f"🔍 Raw response data count: {len(response.data) if response.data else 0}")
            if response.data and len(response.data) > 0:
                first_doc = response.data[0]
                print(f"🔍 First document structure: {list(first_doc.keys())}")
                print(f"🔍 Has embedding: {first_doc.get('embedding') is not None}")
                if first_doc.get('embedding'):
                    embedding_sample = first_doc.get('embedding')
                    print(f"🔍 Embedding type: {type(embedding_sample)}, length: {len(embedding_sample) if embedding_sample else 0}")
                    print(f"🔍 Embedding preview (first 100 chars): {str(embedding_sample)[:100]}...")
            
            # Filter out documents without embeddings manually
            if response.data:
                response.data = [doc for doc in response.data if doc.get('embedding') is not None]
                print(f"🔍 Documents with embeddings after filtering: {len(response.data)}")
            
            if not response.data:
                print("🔍 No documents with embeddings found")
                return []
            
            print(f"🔍 Retrieved {len(response.data)} automation documents with embeddings")
            
            # Calculate similarities manually
            import numpy as np
            import json
            query_vector = np.array(query_embedding)
            
            doc_similarities = []
            
            for doc in response.data:
                if doc.get('embedding'):
                    try:
                        # Parse embedding from string format (stored as JSON string)
                        embedding_str = doc['embedding']
                        if isinstance(embedding_str, str):
                            # Try to parse as JSON array
                            try:
                                embedding_data = json.loads(embedding_str)
                            except json.JSONDecodeError:
                                # If not JSON, try to evaluate as Python literal
                                embedding_data = eval(embedding_str)
                        else:
                            embedding_data = embedding_str
                        
                        doc_vector = np.array(embedding_data)
                        
                        if doc_vector.shape != query_vector.shape:
                            print(f"🔍 Dimension mismatch for doc {doc.get('id')}: query={query_vector.shape}, doc={doc_vector.shape}")
                            continue
                            
                    except Exception as parse_error:
                        print(f"🔍 Failed to parse embedding for doc {doc.get('id')}: {parse_error}")
                        continue
                    
                    # Cosine similarity calculation
                    dot_product = np.dot(query_vector, doc_vector)
                    query_norm = np.linalg.norm(query_vector)
                    doc_norm = np.linalg.norm(doc_vector)
                    
                    cosine_sim = dot_product / (query_norm * doc_norm)
                    
                    if cosine_sim > threshold:
                        # Get category name
                        category_name = 'Uncategorized'
                        if doc.get('automations') and len(doc['automations']) > 0:
                            category_info = doc['automations'][0].get('categories')
                            if category_info:
                                category_name = category_info.get('name', 'Uncategorized')
                        
                        # Format filename as title
                        title = doc.get('filename', 'Unnamed')
                        if title.endswith('.json'):
                            title = title[:-5]  # Remove .json extension
                        title = title.replace('-', ' ').replace('_', ' ').title()
                        
                        doc_similarities.append({
                            'id': doc['id'],
                            'title': title,
                            'short_description': doc.get('short_description', ''),
                            'description': doc.get('description', ''),
                            'url': doc.get('url', ''),
                            'category': category_name,
                            'similarity': float(cosine_sim)
                        })
            
            # Sort by similarity (highest first) and limit
            doc_similarities.sort(key=lambda x: x['similarity'], reverse=True)
            results = doc_similarities[:limit]
            
            print(f"🔍 Found {len(results)} similar automations above threshold {threshold}")
            for i, doc in enumerate(results):
                print(f"🔍 Rank {i+1}: {doc['title']} (similarity: {doc['similarity']:.4f})")
            
            return results
            
        except Exception as e:
            print(f"Error in automation similarity search: {e}")
            return []
    
    async def search_content(self, user_id: int, query_embedding: List[float], limit: int = 5, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Vector similarity search engine for documents
        
        Args:
            user_id: Unused for compatibility (documents are global)
            query_embedding: Query vector embedding from OpenAI text-embedding-3-large (3072 dimensions)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of documents ranked by vector similarity
        """
        try:
            results = []
            
            # Vector search on documents table
            # Table schema: id, content, embedding, metadata, ingestion_date
            # Embedding dimensions: 3072 (OpenAI text-embedding-3-large)
            print(f"🔍 Starting vector search with threshold={threshold}, limit={limit}")
            
            try:
                # Method 1: Use Supabase RPC function for vector similarity search
                try:
                    print("🔍 Trying Supabase RPC function for vector similarity search...")
                    
                    # Create a custom RPC function call for vector search
                    # This avoids URL length limits by sending the vector in the request body
                    response = self.client.rpc('search_similar_documents', {
                        'query_embedding': query_embedding,
                        'similarity_threshold': threshold,
                        'match_count': limit
                    }).execute()
                    
                    print(f"🔍 RPC function returned {len(response.data) if response.data else 0} results")
                    
                    if response.data:
                        # Process RPC results
                        for doc in response.data:
                            similarity = doc.get('similarity', 0)
                            metadata = doc.get('metadata')
                            
                            results.append({
                                'id': metadata.get('file_id'),
                                'title': metadata.get('file_name'),
                                'content_text': doc.get('content'),
                                'type': metadata.get('type'),
                                'similarity': float(similarity)
                            })
                    
                except Exception as rpc_error:
                    print(f"🔍 RPC function failed (function may not exist): {rpc_error}")
                    response = None
                
                # Method 2: Manual similarity calculation with correct Supabase syntax
                if not results:  # Only try if RPC didn't work
                    print("🔍 Trying manual similarity calculation...")
                    
                    try:
                        # Get all documents with embeddings - FIXED SYNTAX
                        all_docs_response = self.client.table('documents').select('id, content, embedding, metadata, ingestion_date').not_('embedding', 'is', 'null').execute()
                        
                        if all_docs_response.data:
                            print(f"🔍 Retrieved {len(all_docs_response.data)} documents with embeddings for manual calculation")
                            
                            # Calculate similarities manually
                            import numpy as np
                            query_vector = np.array(query_embedding)
                            print(f"📊 Query vector shape: {query_vector.shape}, norm: {np.linalg.norm(query_vector):.4f}")
                            
                            doc_similarities = []
                            all_cosine_distances = []  # Track all distances for logging
                            
                            for i, doc in enumerate(all_docs_response.data):
                                if doc.get('embedding'):
                                    doc_vector = np.array(doc['embedding'])
                                    doc_id = doc.get('id', f'doc_{i}')
                                    
                                    # Cosine similarity calculation
                                    dot_product = np.dot(query_vector, doc_vector)
                                    query_norm = np.linalg.norm(query_vector)
                                    doc_norm = np.linalg.norm(doc_vector)
                                    
                                    cosine_sim = dot_product / (query_norm * doc_norm)
                                    
                                    # Log individual calculation
                                    print(f"📄 Doc {doc_id}: dot_product={dot_product:.4f}, doc_norm={doc_norm:.4f}, cosine_sim={cosine_sim:.4f}")
                                    
                                    all_cosine_distances.append({
                                        'doc_id': doc_id,
                                        'cosine_similarity': float(cosine_sim),
                                        'dot_product': float(dot_product),
                                        'doc_norm': float(doc_norm),
                                        'above_threshold': cosine_sim > threshold
                                    })
                                    
                                    if cosine_sim > threshold:
                                        doc_similarities.append({
                                            **doc,
                                            'similarity': float(cosine_sim)
                                        })
                            
                            # Log complete array of cosine distances
                            print(f"\n📊 COMPLETE COSINE DISTANCES ARRAY:")
                            print(f"📊 Total documents processed: {len(all_cosine_distances)}")
                            print(f"📊 Threshold: {threshold}")
                            
                            for i, dist in enumerate(all_cosine_distances):
                                status = "✅ ABOVE" if dist['above_threshold'] else "❌ BELOW"
                                print(f"📊 [{i:2d}] Doc {dist['doc_id']:>3}: {dist['cosine_similarity']:>7.4f} {status} threshold")
                            
                            # Sort by similarity (highest first) and limit
                            doc_similarities.sort(key=lambda x: x['similarity'], reverse=True)
                            response_data = doc_similarities[:limit]
                            
                            print(f"\n📊 SIMILARITY RANKING:")
                            for i, doc in enumerate(response_data):
                                print(f"📊 Rank {i+1}: Doc {doc.get('id')} = {doc['similarity']:.4f}")
                            
                            print(f"🔍 Manual calculation found {len(response_data)} documents above threshold {threshold}")


                            # Process RPC results
                            for doc in all_docs_response.data:
                                similarity = doc.get('similarity', 0)
                                metadata = doc.get('metadata')
                                print('metadata: ', metadata.get('file_id'))
                            
                                results.append({
                                    'id': metadata.get('file_id'),
                                    'title': metadata.get('file_name'),
                                    'content_text': doc.get('content'),
                                    'type': metadata.get('type'),
                                    'similarity': float(similarity)
                                })                            
                            
                        else:
                            print("🔍 No documents with embeddings found")
                            
                    except Exception as manual_error:
                        print(f"🔍 Manual similarity calculation failed: {manual_error}")
                        import traceback
                        traceback.print_exc()
                
                # Results are already processed in the methods above
                pass
                
            except Exception as e:
                print(f"Error in vector search: {e}")
                # Ultimate fallback: basic document retrieval (no similarity)
                try:
                    print("🔄 Ultimate fallback: basic document retrieval without similarity...")
                    response = self.client.table('documents').select('id, content, metadata, ingestion_date').limit(limit).execute()
                    
                    if response.data:
                        print(f"🔄 Fallback retrieved {len(response.data)} documents")
                        for doc in response.data:
                            similarity = doc.get('similarity', 0)
                            metadata = doc.get('metadata')
                            print('metadata: ', metadata.get('file_id'))
                            
                            results.append({
                                'id': metadata.get('file_id'),
                                'title': metadata.get('file_name'),
                                'content_text': doc.get('content'),
                                'type': metadata.get('type'),                                    'similarity': float(similarity)
                            })         
                            
                except Exception as fallback_error:
                    print(f"⚠️ All search methods failed: {fallback_error}")
            
            # Sort by similarity (highest first) and apply limit
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            final_results = results[:limit]
            
            if final_results:
                print(f"🎯 Vector Search Complete: Returning {len(final_results)} results (top similarity: {final_results[0]['similarity']:.4f})")
            else:
                print("🎯 Vector Search Complete: No results found")
                
            return final_results
            
        except Exception as e:
            print(f"Error in search_content: {e}")
            return []
    
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[User]:
        """Create user only if doesn't exist - for handlers compatibility"""
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return existing_user  # Don't update, just return existing user
            
        # Only create new user if doesn't exist
        user_data = {
            'telegram_id': telegram_id,
            'username': username
        }
        # Remove None values to avoid column errors
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        try:
            response = self.client.table('users').insert(user_data).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def update_user_payment_status(self, telegram_id: int, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            response = self.client.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            
            if response.data:
                print(f"✅ Updated payment status for user {telegram_id}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user {telegram_id}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status: {e}")
            return False
    
    async def update_user_payment_status_by_email(self, email: str, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status by email (if email field exists)"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            # Note: This assumes you have an email field in users table
            # You might need to add email field to users table first
            response = self.client.table('users').update(update_data).eq('email', email).execute()
            
            if response.data:
                print(f"✅ Updated payment status for user with email {email}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user with email {email}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status by email: {e}")
            return False