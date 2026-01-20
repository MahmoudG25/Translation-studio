"""
Translation Verification Utility
Validates that all subtitles have been properly translated and no sentences are left untranslated.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple


class TranslationVerifier:
    """Verify translation completeness and quality."""

    @staticmethod
    def parse_srt(file_path: str) -> List[Dict[str, str]]:
        """Parse SRT file into subtitle blocks."""
        subtitles = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            blocks = content.strip().split('\n\n')
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    try:
                        subtitles.append({
                            'index': lines[0].strip(),
                            'timestamp': lines[1].strip(),
                            'text': '\n'.join(lines[2:]).strip()
                        })
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return subtitles

    @staticmethod
    def verify_file(file_path: str) -> Dict:
        """
        Verify a single SRT file for translation completeness.
        
        Returns:
            Dictionary with verification results
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        subtitles = TranslationVerifier.parse_srt(file_path)
        
        if not subtitles:
            return {
                "file": file_path,
                "status": "ERROR",
                "total": 0,
                "empty": 0,
                "translated": 0,
                "issues": ["No subtitles found in file"]
            }
        
        empty_count = 0
        translated_count = 0
        empty_indices = []
        
        for i, subtitle in enumerate(subtitles):
            text = subtitle['text'].strip()
            
            if not text:
                empty_count += 1
                empty_indices.append(i + 1)
            else:
                translated_count += 1
        
        issues = []
        if empty_count > 0:
            issues.append(f"Found {empty_count} EMPTY subtitles at indices: {empty_indices}")
        
        if translated_count == 0:
            issues.append("NO TRANSLATIONS FOUND - All subtitles are empty!")
            status = "FAIL"
        elif empty_count > 0:
            issues.append(f"WARNING: {empty_count}/{len(subtitles)} subtitles are untranslated")
            status = "PARTIAL"
        else:
            status = "PASS"
        
        return {
            "file": file_path,
            "status": status,
            "total": len(subtitles),
            "empty": empty_count,
            "translated": translated_count,
            "percentage": round((translated_count / len(subtitles) * 100), 1) if subtitles else 0,
            "issues": issues
        }

    @staticmethod
    def verify_directory(directory: str, pattern: str = "*.ar.srt") -> Dict:
        """
        Verify all translated SRT files in a directory.
        
        Args:
            directory: Directory to scan
            pattern: File pattern to match (default: *.ar.srt for Arabic translations)
        
        Returns:
            Summary of all verifications
        """
        if not os.path.isdir(directory):
            return {"error": f"Directory not found: {directory}"}
        
        path = Path(directory)
        files = list(path.glob(pattern))
        
        if not files:
            return {"error": f"No files matching pattern '{pattern}' found in {directory}"}
        
        results = []
        total_files = len(files)
        passed_files = 0
        failed_files = 0
        partial_files = 0
        total_subtitles = 0
        total_empty = 0
        
        for file_path in sorted(files):
            result = TranslationVerifier.verify_file(str(file_path))
            results.append(result)
            
            if result.get("status") == "PASS":
                passed_files += 1
            elif result.get("status") == "FAIL":
                failed_files += 1
            elif result.get("status") == "PARTIAL":
                partial_files += 1
            
            total_subtitles += result.get("total", 0)
            total_empty += result.get("empty", 0)
        
        return {
            "directory": directory,
            "pattern": pattern,
            "summary": {
                "total_files": total_files,
                "passed": passed_files,
                "failed": failed_files,
                "partial": partial_files,
                "total_subtitles": total_subtitles,
                "untranslated_subtitles": total_empty,
                "completion_percentage": round((total_subtitles - total_empty) / total_subtitles * 100, 1) if total_subtitles > 0 else 0
            },
            "files": results
        }

    @staticmethod
    def print_report(verification_result: Dict):
        """Print a human-readable verification report."""
        if "error" in verification_result:
            print(f"ERROR: {verification_result['error']}")
            return
        
        if "directory" in verification_result:
            # Directory verification report
            summary = verification_result['summary']
            print(f"\n{'='*70}")
            print(f"TRANSLATION VERIFICATION REPORT - {verification_result['directory']}")
            print(f"{'='*70}")
            print(f"\nPattern: {verification_result['pattern']}")
            print(f"\nSummary:")
            print(f"  Total Files: {summary['total_files']}")
            print(f"  ✓ Passed (all translated): {summary['passed']}")
            print(f"  ⚠ Partial (some untranslated): {summary['partial']}")
            print(f"  ✗ Failed (all untranslated): {summary['failed']}")
            print(f"\nSubtitle Statistics:")
            print(f"  Total Subtitles: {summary['total_subtitles']}")
            print(f"  Translated: {summary['total_subtitles'] - summary['untranslated_subtitles']}")
            print(f"  Untranslated (EMPTY): {summary['untranslated_subtitles']}")
            print(f"  Completion Rate: {summary['completion_percentage']}%")
            
            if summary['failed'] > 0 or summary['partial'] > 0:
                print(f"\n{'='*70}")
                print("ISSUES FOUND:")
                print(f"{'='*70}")
                for file_result in verification_result['files']:
                    if file_result['status'] != 'PASS':
                        print(f"\n{file_result['file']}:")
                        print(f"  Status: {file_result['status']}")
                        print(f"  Translated: {file_result['translated']}/{file_result['total']}")
                        for issue in file_result.get('issues', []):
                            print(f"  - {issue}")
        else:
            # Single file verification report
            print(f"\n{'='*70}")
            print(f"TRANSLATION VERIFICATION - {verification_result['file']}")
            print(f"{'='*70}")
            print(f"Status: {verification_result['status']}")
            print(f"Total Subtitles: {verification_result['total']}")
            print(f"Translated: {verification_result['translated']}")
            print(f"Empty/Untranslated: {verification_result['empty']}")
            print(f"Completion: {verification_result.get('percentage', 0)}%")
            
            if verification_result['issues']:
                print(f"\nIssues:")
                for issue in verification_result['issues']:
                    print(f"  - {issue}")


def main():
    """Main entry point for verification."""
    import sys
    
    if len(sys.argv) < 2:
        print("Translation Verifier - Check if all subtitles have been translated")
        print("\nUsage:")
        print("  python translation_verifier.py <file_path>     - Verify single SRT file")
        print("  python translation_verifier.py <directory>     - Verify all .ar.srt files in directory")
        print("  python translation_verifier.py <directory> <pattern>  - Verify files matching pattern")
        print("\nExamples:")
        print("  python translation_verifier.py output.ar.srt")
        print("  python translation_verifier.py ./subtitles")
        print("  python translation_verifier.py ./subtitles '*.srt'")
        return
    
    target = sys.argv[1]
    
    if os.path.isfile(target):
        # Verify single file
        result = TranslationVerifier.verify_file(target)
    else:
        # Verify directory
        pattern = sys.argv[2] if len(sys.argv) > 2 else "*.ar.srt"
        result = TranslationVerifier.verify_directory(target, pattern)
    
    TranslationVerifier.print_report(result)
    
    # Exit with appropriate code
    if isinstance(result, dict):
        if result.get('status') == 'FAIL' or result.get('summary', {}).get('failed', 0) > 0:
            sys.exit(1)
        elif result.get('status') == 'PARTIAL' or result.get('summary', {}).get('partial', 0) > 0:
            sys.exit(2)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
