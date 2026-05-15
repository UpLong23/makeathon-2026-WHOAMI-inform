# Tech
Hallucination --> Reflection, Deterministic, Confidence score, metacognitive prompting

About Hallucination
1) It generates information that does not exist
2) It finds information, but it is wrong

# Pipeline
1) Data Prep --> OCR
2) Vectorization --> Vectorization
3) RAG model
4) Deployment
5) Evaluation
Στο 3-4 πρέπει να γίνει επιλογή μοντέλου.

# Observations/Questions
**Πως θα κρατάει το μοντέλο την προηγούμενη απάντηση και το περιεχόμενό της
ώστε αν γίνει εκ νέου ερώτηση περί του τιμολογίου, να γνωρίζει που να ψάξει;** 

**Πόσο κοστίζει το token;**

**Πως θα επιλέγει το μοντέλο αν πρέπει να φέρει νέα πληροφορία ή αν μπορεί να αξιοποιήσει την υπάρχουσα;**

**Αν έχεις ένα ανοικτό αρχείο στο preview, αυτόματα να παίρνει ως reference αυτό που έχεις ήδη ανοικτό.**

**Πόση πληροφορία θα μου φέρνει;**

**Πως θα κρατάμε τα chats;**
Απάντηση: Θα πρέπει να σώζουμε σε μία βάση όλη την συζήτηση που έχει γινεί. 

## UI
Να υπάρχουν tabs στο Preview, ώστε να μπορείς να εναλλάσεις αυτά που βλέπεις
Να υπάρχει επιλογή παρόχου μοντέλου