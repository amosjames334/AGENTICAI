"""
Demo script for the new modular preprocessing pipeline

Shows how to use:
- TextCleaner for advanced text cleaning
- DocumentChunker for token-based chunking with overlap
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from DataPipeline.preprocessing import TextCleaner, DocumentChunker, Chunk


def demo_text_cleaner():
    """Demonstrate TextCleaner usage"""
    print("=" * 80)
    print("TEXT CLEANER DEMO")
    print("=" * 80)
    
    # Sample academic paper text with various artifacts
    sample_text = """
    Neural Networks for Natural Language Processing
    
    John Doe¹, Jane Smith²
    ¹MIT, jdoe@mit.edu
    ²Stanford, jsmith@stanford.edu
    
    Abstract
    
    We present a novel approach to NLP using transformers [1,2,3]. Our method 
    achieves state-of-the-art results (BLEU score: 42.5). See https://ourpaper.com
    for more details. The architecture builds on previous work (Vaswani et al., 2017)
    and improves upon it significantly (2023).
    
    1. Introduction
    
    Natural language processing has seen tremendous advances in recent years. 
    The transformer architecture (Vaswani et al., 2017) revolutionized the field.
    Our contributions include:
    - Novel attention mechanism
    - Improved training procedure
    
    
    
    5. References
    
    [1] Vaswani, A., et al. (2017). Attention is all you need.
    [2] Devlin, J., et al. (2019). BERT.
    [3] Brown, T., et al. (2020). GPT-3.
    """
    
    print("\n1. Basic Cleaning (URLs + Emails)")
    print("-" * 80)
    cleaner = TextCleaner(remove_citations=False, remove_urls=True)
    cleaned = cleaner.clean(sample_text)
    print(f"Original length: {len(sample_text)} chars")
    print(f"Cleaned length: {len(cleaned)} chars")
    print(f"\nCleaned text preview:\n{cleaned[:300]}...")
    
    print("\n\n2. Advanced Cleaning (Citations + References + URLs + Emails)")
    print("-" * 80)
    cleaner_advanced = TextCleaner(
        remove_citations=True,
        remove_urls=True,
        remove_emails=True,
        remove_references=True
    )
    cleaned_advanced = cleaner_advanced.clean(sample_text)
    stats = cleaner_advanced.get_stats(sample_text, cleaned_advanced)
    
    print(f"Original length: {stats['original_length']} chars")
    print(f"Cleaned length: {stats['cleaned_length']} chars")
    print(f"Reduction: {stats['reduction_percent']:.1f}%")
    print(f"\nCleaned text:\n{cleaned_advanced}")
    
    print("\n\n3. Batch Cleaning")
    print("-" * 80)
    texts = [
        "Paper 1 with citations [1,2] and URL https://example.com",
        "Paper 2 with email author@university.edu and more [3,4,5]",
        "Paper 3 clean text without artifacts"
    ]
    cleaned_batch = cleaner_advanced.clean_batch(texts)
    for i, (original, cleaned) in enumerate(zip(texts, cleaned_batch)):
        print(f"\nText {i+1}:")
        print(f"  Original: {original}")
        print(f"  Cleaned:  {cleaned}")


def demo_document_chunker():
    """Demonstrate DocumentChunker usage"""
    print("\n\n" + "=" * 80)
    print("DOCUMENT CHUNKER DEMO")
    print("=" * 80)
    
    # Sample paper text
    sample_paper = """
    Introduction to Neural Networks
    
    Neural networks are computational models inspired by biological neural networks.
    They consist of interconnected nodes called neurons that process information.
    The basic building block is the artificial neuron which receives inputs, 
    processes them, and produces an output.
    
    Architecture and Components
    
    A typical neural network consists of three types of layers: input layers,
    hidden layers, and output layers. The input layer receives the raw data.
    Hidden layers perform intermediate computations and feature extraction.
    The output layer produces the final prediction or classification.
    
    Training Process
    
    Neural networks learn through a process called backpropagation. During training,
    the network makes predictions on training data. The error between predicted
    and actual values is calculated using a loss function. This error is then
    propagated backwards through the network to update the weights. The process
    repeats for many iterations until the network converges to an optimal solution.
    
    Applications
    
    Neural networks have numerous applications across various domains. In computer
    vision, convolutional neural networks excel at image recognition tasks. In
    natural language processing, recurrent and transformer networks process text.
    In reinforcement learning, deep neural networks enable agents to learn complex
    behaviors through interaction with environments.
    """
    
    print("\n1. Basic Chunking (Token-based, 512 tokens, 50 overlap)")
    print("-" * 80)
    chunker = DocumentChunker(chunk_size=512, overlap=50, min_chunk_size=100)
    chunks = chunker.chunk_document(
        text=sample_paper,
        paper_id="neural_networks_intro",
        preserve_sentences=True
    )
    
    print(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk.chunk_id}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Position: {chunk.position}")
        print(f"  Char range: {chunk.start_char}-{chunk.end_char}")
        print(f"  Preview: {chunk.text[:100]}...")
    
    stats = chunker.get_stats(chunks)
    print(f"\nChunking Statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Avg tokens/chunk: {stats['avg_tokens_per_chunk']:.1f}")
    print(f"  Min tokens: {stats['min_tokens']}")
    print(f"  Max tokens: {stats['max_tokens']}")
    
    print("\n\n2. Paragraph-Preserving Chunking")
    print("-" * 80)
    chunks_para = chunker.chunk_document(
        text=sample_paper,
        paper_id="neural_networks_intro",
        preserve_sentences=True,
        preserve_paragraphs=True
    )
    
    print(f"Created {len(chunks_para)} chunks")
    for i, chunk in enumerate(chunks_para):
        print(f"\nChunk {i+1}:")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  First 150 chars: {chunk.text[:150]}...")
    
    print("\n\n3. Smaller Chunks (256 tokens)")
    print("-" * 80)
    chunker_small = DocumentChunker(chunk_size=256, overlap=25, min_chunk_size=50)
    chunks_small = chunker_small.chunk_document(
        text=sample_paper,
        paper_id="neural_networks_intro",
        preserve_sentences=True
    )
    
    print(f"Created {len(chunks_small)} chunks (vs {len(chunks)} with 512 tokens)")
    stats_small = chunker_small.get_stats(chunks_small)
    print(f"Average tokens per chunk: {stats_small['avg_tokens_per_chunk']:.1f}")


def demo_full_pipeline():
    """Demonstrate full pipeline: Clean + Chunk"""
    print("\n\n" + "=" * 80)
    print("FULL PIPELINE DEMO (Clean → Chunk)")
    print("=" * 80)
    
    # Raw academic paper with artifacts
    raw_paper = """
    Advances in Deep Learning [1,2,3]
    
    Authors: Smith et al. (2023)
    Contact: smith@university.edu
    
    Our work builds on previous research (Doe, 2022) and introduces novel
    architectures. Visit https://ourproject.org for code and data [4].
    
    The proposed method achieves 95% accuracy on benchmark datasets.
    See Figure 1 for detailed results. Citation: (Smith et al., 2023).
    
    
    
    
    
    References
    [1] LeCun et al. Deep Learning. Nature 2015.
    [2] Goodfellow et al. Deep Learning Book. 2016.
    """ * 3  # Repeat to make it longer
    
    print(f"Raw paper length: {len(raw_paper)} chars")
    print(f"Estimated chunks: {DocumentChunker(chunk_size=512).estimate_chunk_count(raw_paper)}")
    
    # Step 1: Clean
    print("\nStep 1: Cleaning...")
    cleaner = TextCleaner(
        remove_citations=True,
        remove_urls=True,
        remove_emails=True,
        remove_references=True
    )
    cleaned = cleaner.clean(raw_paper)
    stats = cleaner.get_stats(raw_paper, cleaned)
    print(f"  Cleaned: {stats['original_length']} → {stats['cleaned_length']} chars")
    print(f"  Reduction: {stats['reduction_percent']:.1f}%")
    
    # Step 2: Chunk
    print("\nStep 2: Chunking...")
    chunker = DocumentChunker(chunk_size=512, overlap=50)
    chunks = chunker.chunk_document(
        text=cleaned,
        paper_id="advances_deep_learning",
        preserve_sentences=True
    )
    chunk_stats = chunker.get_stats(chunks)
    print(f"  Created {len(chunks)} chunks")
    print(f"  Avg tokens: {chunk_stats['avg_tokens_per_chunk']:.1f}")
    
    # Display results
    print("\nFinal Chunks:")
    for i, chunk in enumerate(chunks[:3]):  # Show first 3
        print(f"\n  Chunk {i+1} ({chunk.token_count} tokens):")
        print(f"    {chunk.text[:150]}...")


def main():
    """Run all demos"""
    print("\n🚀 Preprocessing Pipeline Demo\n")
    
    try:
        demo_text_cleaner()
        demo_document_chunker()
        demo_full_pipeline()
        
        print("\n\n" + "=" * 80)
        print("✅ Demo Complete!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  • TextCleaner removes citations, URLs, emails, and references")
        print("  • DocumentChunker creates token-based chunks with overlap")
        print("  • Both components are highly configurable")
        print("  • Easily integrate into your document processing pipeline")
        print("\nUsage:")
        print("  from DataPipeline.preprocessing import TextCleaner, DocumentChunker")
        print("  cleaner = TextCleaner(remove_citations=True)")
        print("  chunker = DocumentChunker(chunk_size=512, overlap=50)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

