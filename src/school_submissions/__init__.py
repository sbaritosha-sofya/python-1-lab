__version__ = "1.2.0"

from .analysis_service import AnalysisService
from .comparison import PairSimilarity, compare_features, find_top_k
from .features import (
    AST_METHOD,
    FEATURE_VERSION,
    TOKEN_METHOD,
    FeatureSet,
    build_ast_features,
    build_features,
    build_token_features,
)
from .analyzers import (
    AnalysisContext,
    AnalysisReport,
    Analyzer,
    AnalyzerRegistry,
    LengthAnalyzer,
    TemplateAnalyzer,
)
from .models import Assignment, Submission
from .pipeline import FeatureStream, collect_features, index_size_bytes, iter_features
from .service import SubmissionService
from .sources import InMemorySource, JSONLSource, Source

__all__ = [
    "AnalysisContext",
    "AnalysisReport",
    "AnalysisService",
    "Analyzer",
    "AnalyzerRegistry",
    "AST_METHOD",
    "Assignment",
    "FEATURE_VERSION",
    "FeatureSet",
    "FeatureStream",
    "InMemorySource",
    "JSONLSource",
    "LengthAnalyzer",
    "PairSimilarity",
    "Source",
    "TOKEN_METHOD",
    "Submission",
    "SubmissionService",
    "TemplateAnalyzer",
    "build_ast_features",
    "build_features",
    "build_token_features",
    "collect_features",
    "compare_features",
    "find_top_k",
    "index_size_bytes",
    "iter_features",
]
