from textblob import TextBlob

class SentimentService:
    @staticmethod
    def analyze_text(text: str) -> dict:
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment
            return {
                "polarity": float(sentiment.polarity),
                "subjectivity": float(sentiment.subjectivity),
                "label": "positive" if sentiment.polarity > 0 else "negative" if sentiment.polarity < 0 else "neutral"
            }
        except Exception as e:
            print(f"TextBlob sentiment analysis failed, using fallback heuristic: {e}")
            # Robust, keyword-based sentiment analyzer as a fallback
            positive_words = {
                "good", "great", "excellent", "happy", "love", "awesome", "nice", 
                "fantastic", "wonderful", "glad", "best", "super", "cool", "perfect",
                "resolved", "solved", "working", "success", "successful", "correct"
            }
            negative_words = {
                "bad", "terrible", "worst", "sad", "hate", "angry", "poor", "broken",
                "fail", "error", "issue", "problem", "difficult", "unable", "cannot",
                "crash", "defect", "flaw", "fault", "wrong", "failure", "unfortunate"
            }
            
            # Clean and split words
            import re
            words = re.findall(r'\b\w+\b', text.lower())
            
            pos_count = sum(1 for w in words if w in positive_words)
            neg_count = sum(1 for w in words if w in negative_words)
            
            polarity = 0.0
            if pos_count or neg_count:
                polarity = (pos_count - neg_count) / (pos_count + neg_count)
                
            return {
                "polarity": polarity,
                "subjectivity": 0.5,  # neutral default
                "label": "positive" if polarity > 0.1 else "negative" if polarity < -0.1 else "neutral"
            }

sentiment_service = SentimentService()
