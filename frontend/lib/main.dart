import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image_picker/image_picker.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Assistant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, String>> _messages = [];
  String _baseUrl = "https://kebab-retrace-transpose.ngrok-free.dev";
  final ScrollController _scrollController = ScrollController();

  // Speech to Text (Optimized & Real-time)
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  bool _speechEnabled = false;

  // Text to Speech (Voice Output)
  final FlutterTts _flutterTts = FlutterTts();
  bool _isVoiceOutputEnabled = true;

  // Multimodal Attachment Support
  final ImagePicker _picker = ImagePicker();
  XFile? _selectedAttachment;
  String? _attachmentMime;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _loadLocalHistory();
    _initSpeech();
    _initTts();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _speech.stop();
    _flutterTts.stop();
    super.dispose();
  }

  Future<void> _initSpeech() async {
    try {
      _speechEnabled = await _speech.initialize(
        onStatus: (status) {
          debugPrint("Speech status: $status");
          if (status == "done" || status == "notListening") {
            setState(() => _isListening = false);
          }
        },
        onError: (error) {
          debugPrint("Speech error: $error");
          setState(() => _isListening = false);
        },
      );
      setState(() {});
    } catch (e) {
      debugPrint("Speech initialization failed: $e");
    }
  }

  Future<void> _initTts() async {
    try {
      await _flutterTts.setLanguage("en-US");
      await _flutterTts.setSpeechRate(0.5);
      await _flutterTts.setVolume(1.0);
      await _flutterTts.setPitch(1.0);
    } catch (e) {
      debugPrint("TTS init failed: $e");
    }
  }

  Future<void> _loadSettings() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/settings.json');
      if (await file.exists()) {
        final data = jsonDecode(await file.readAsString());
        setState(() {
          _baseUrl = data['baseUrl'] ?? _baseUrl;
        });
      }
    } catch (e) {
      debugPrint("Error loading settings: $e");
    }
  }

  Future<void> _saveSettings() async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File('${dir.path}/settings.json');
    await file.writeAsString(jsonEncode({'baseUrl': _baseUrl}));
  }

  Future<void> _loadLocalHistory() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/chat_history.json');
      if (await file.exists()) {
        final List<dynamic> data = jsonDecode(await file.readAsString());
        setState(() {
          _messages.clear();
          _messages.addAll(data.map((m) => Map<String, String>.from(m)).toList());
        });
        _scrollToBottom();
      }
      _syncWithServer();
    } catch (e) {
      debugPrint("Error loading history: $e");
    }
  }

  Future<void> _saveLocalHistory() async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File('${dir.path}/chat_history.json');
    await file.writeAsString(jsonEncode(_messages));
  }

  Future<void> _syncWithServer() async {
    try {
      final response = await http.get(Uri.parse("$_baseUrl/chat/history?user_id=default"));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        setState(() {
          _messages.clear();
          _messages.addAll(data.map((m) => Map<String, String>.from(m)).toList());
        });
        _saveLocalHistory();
        _scrollToBottom();
      }
    } catch (e) {
      debugPrint("Sync failed: $e");
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(String text) async {
    if (text.isEmpty && _selectedAttachment == null) return;
    
    final promptText = text.isNotEmpty ? text : "Analyze the attached file.";
    
    setState(() {
      _messages.add({"role": "user", "content": promptText});
      _controller.clear();
    });
    _scrollToBottom();
    _saveLocalHistory();

    try {
      String? base64Attachment;
      String? mimeType;
      
      if (_selectedAttachment != null) {
        final bytes = await File(_selectedAttachment!.path).readAsBytes();
        base64Attachment = base64Encode(bytes);
        mimeType = _attachmentMime;
      }
      
      // Clear attachment immediately in UI
      setState(() {
        _selectedAttachment = null;
        _attachmentMime = null;
      });

      final bodyMap = {
        "message": promptText,
        "user_id": "default",
      };
      if (base64Attachment != null) {
        bodyMap["attachment"] = base64Attachment;
        bodyMap["attachment_mime"] = mimeType ?? "";
      }

      final response = await http.post(
        Uri.parse("$_baseUrl/chat"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(bodyMap),
      ).timeout(const Duration(seconds: 45));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final reply = data["response"];
        
        setState(() {
          _messages.add({"role": "assistant", "content": reply});
        });
        _saveLocalHistory();
        _scrollToBottom();
        
        // Speak response aloud if TTS enabled
        if (_isVoiceOutputEnabled) {
          _speak(reply);
        }
        
        // If it was a forget/clear command, re-sync history to reflect changes immediately
        final lowerText = promptText.toLowerCase().trim();
        final isForgetCommand = any(lowerText.startsWith(prefix) for prefix in [
          "forget about", "forget yesterday", "forget the last", "forget my preference", 
          "delete my memory", "clear memory"
        ]) || lowerText == "clear all memory" || lowerText == "clear history" || lowerText == "forget everything";
        
        if (isForgetCommand) {
          _syncWithServer();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    }
  }

  // Helper helper to support list matching in Dart
  bool any(Iterable<bool> iterable) {
    for (final element in iterable) {
      if (element) return true;
    }
    return false;
  }

  Future<void> _speak(String text) async {
    await _flutterTts.stop();
    // Strip markdown symbols for natural audio speech synthesis
    final cleanText = text
        .replaceAll(RegExp(r'\*|_|#|`|>|\[|\]'), '')
        .replaceAll(RegExp(r'\n+'), '. ');
    await _flutterTts.speak(cleanText);
  }

  Future<void> _clearHistory() async {
    setState(() => _messages.clear());
    await _saveLocalHistory();
    try {
      await http.delete(Uri.parse("$_baseUrl/chat/history?user_id=default"));
    } catch (e) {
      debugPrint("Remote clear failed: $e");
    }
  }

  Future<void> _deleteMessage(String id) async {
    try {
      final response = await http.delete(Uri.parse("$_baseUrl/chat/history/$id"));
      if (response.statusCode == 200) {
        _syncWithServer();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Failed to delete entry: ${response.body}")),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error deleting entry: $e")),
      );
    }
  }

  void _showSettings() {
    final TextEditingController urlController = TextEditingController(text: _baseUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Settings"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: urlController,
              decoration: const InputDecoration(labelText: "Backend URL", hintText: "https://..."),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: () {
                _clearHistory();
                Navigator.pop(context);
              },
              icon: const Icon(Icons.delete_sweep),
              label: const Text("Clear All History"),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.red[900], foregroundColor: Colors.white),
            )
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          TextButton(
            onPressed: () {
              setState(() => _baseUrl = urlController.text);
              _saveSettings();
              Navigator.pop(context);
              _syncWithServer();
            },
            child: const Text("Save"),
          ),
        ],
      ),
    );
  }

  // Real-time optimized Speech listening
  Future<void> _toggleListening() async {
    if (_isListening) {
      await _speech.stop();
      setState(() => _isListening = false);
    } else {
      if (!_speechEnabled) {
        await _initSpeech();
      }
      if (_speechEnabled) {
        setState(() => _isListening = true);
        await _speech.listen(
          onResult: (result) {
            setState(() {
              _controller.text = result.recognizedWords;
            });
          },
          listenFor: const Duration(seconds: 30),
          pauseFor: const Duration(seconds: 2), // reduced silence detection timeout for immediate processing!
          listenMode: stt.ListenMode.confirmation,
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Speech recognition not available")),
        );
      }
    }
  }

  Future<void> _showAttachmentPicker() async {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text("Choose Photo from Gallery"),
              onPressed: () {
                Navigator.pop(context);
                _pickAttachment(ImageSource.gallery, isVideo: false);
              },
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text("Take Photo with Camera"),
              onPressed: () {
                Navigator.pop(context);
                _pickAttachment(ImageSource.camera, isVideo: false);
              },
            ),
            ListTile(
              leading: const Icon(Icons.video_library),
              title: const Text("Choose Video from Gallery"),
              onPressed: () {
                Navigator.pop(context);
                _pickAttachment(ImageSource.gallery, isVideo: true);
              },
            ),
            ListTile(
              leading: const Icon(Icons.videocam),
              title: const Text("Take Video with Camera"),
              onPressed: () {
                Navigator.pop(context);
                _pickAttachment(ImageSource.camera, isVideo: true);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickAttachment(ImageSource source, {required bool isVideo}) async {
    try {
      final XFile? file = isVideo 
          ? await _picker.pickVideo(source: source)
          : await _picker.pickImage(source: source);
          
      if (file != null) {
        final extension = file.path.split('.').last.toLowerCase();
        String mimeType = isVideo ? "video/mp4" : "image/jpeg";
        if (extension == "png") {
          mimeType = "image/png";
        } else if (extension == "gif") {
          mimeType = "image/gif";
        } else if (extension == "webp") {
          mimeType = "image/webp";
        } else if (extension == "mov") {
          mimeType = "video/quicktime";
        } else if (extension == "avi") {
          mimeType = "video/x-msvideo";
        }
        
        setState(() {
          _selectedAttachment = file;
          _attachmentMime = mimeType;
        });
      }
    } catch (e) {
      debugPrint("Error picking attachment: $e");
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error picking attachment: $e")),
      );
    }
  }

  Widget _buildAttachmentPreview() {
    if (_selectedAttachment == null) return const SizedBox.shrink();
    
    final isImage = _attachmentMime?.startsWith('image/') ?? false;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Colors.grey[900],
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: isImage
                ? Image.file(
                    File(_selectedAttachment!.path),
                    width: 50,
                    height: 50,
                    fit: BoxFit.cover,
                  )
                : Container(
                    width: 50,
                    height: 50,
                    color: Colors.deepPurple[900],
                    child: const Icon(Icons.video_library, color: Colors.white),
                  ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _selectedAttachment!.name,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  _attachmentMime ?? "File",
                  style: TextStyle(color: Colors.grey[400], fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.redAccent),
            onPressed: () {
              setState(() {
                _selectedAttachment = null;
                _attachmentMime = null;
              });
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Personal AI Assistant"),
        actions: [
          IconButton(
            icon: Icon(
              _isVoiceOutputEnabled ? Icons.volume_up : Icons.volume_off,
              color: _isVoiceOutputEnabled ? Colors.deepPurpleAccent : Colors.grey,
            ),
            onPressed: () {
              setState(() {
                _isVoiceOutputEnabled = !_isVoiceOutputEnabled;
              });
              if (!_isVoiceOutputEnabled) {
                _flutterTts.stop();
              }
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(_isVoiceOutputEnabled ? "Voice Output Enabled" : "Voice Output Muted"),
                  duration: const Duration(seconds: 1),
                ),
              );
            },
            tooltip: _isVoiceOutputEnabled ? "Mute Voice Output" : "Unmute Voice Output",
          ),
          IconButton(
            icon: const Icon(Icons.settings), 
            onPressed: _showSettings
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(8.0),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg["role"] == "user";
                final msgId = msg["id"];

                return Row(
                  mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    if (!isUser && msgId != null)
                      IconButton(
                        icon: Icon(Icons.delete_outline, size: 18, color: Colors.grey[600]),
                        onPressed: () => _deleteMessage(msgId),
                        tooltip: "Delete memory entry",
                      ),
                    Flexible(
                      child: Container(
                        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: isUser ? Colors.deepPurple[700] : Colors.grey[850],
                          borderRadius: BorderRadius.circular(16).copyWith(
                            bottomRight: isUser ? const Radius.circular(0) : const Radius.circular(16),
                            bottomLeft: isUser ? const Radius.circular(16) : const Radius.circular(0),
                          ),
                        ),
                        child: MarkdownBody(
                          data: msg["content"] ?? "",
                          styleSheet: MarkdownStyleSheet(
                            p: const TextStyle(color: Colors.white, fontSize: 16),
                          ),
                        ),
                      ),
                    ),
                    if (isUser && msgId != null)
                      IconButton(
                        icon: Icon(Icons.delete_outline, size: 18, color: Colors.grey[600]),
                        onPressed: () => _deleteMessage(msgId),
                        tooltip: "Delete memory entry",
                      ),
                  ],
                );
              },
            ),
          ),
          _buildAttachmentPreview(),
          Container(
            padding: const EdgeInsets.all(8.0),
            decoration: BoxDecoration(color: Colors.black26, border: Border(top: BorderSide(color: Colors.grey[800]!))),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.attach_file, color: Colors.blueAccent),
                  onPressed: _showAttachmentPicker,
                  tooltip: "Add Photo/Video",
                ),
                IconButton(
                  icon: Icon(_isListening ? Icons.stop : Icons.mic, color: _isListening ? Colors.red : Colors.blueAccent),
                  onPressed: _toggleListening,
                  tooltip: "Voice Input",
                ),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: _isListening ? "Listening..." : "Ask anything...",
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(25), borderSide: BorderSide.none),
                      filled: true,
                      fillColor: Colors.grey[900],
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                    ),
                    onSubmitted: _sendMessage,
                  ),
                ),
                const SizedBox(width: 8),
                CircleAvatar(
                  backgroundColor: Colors.deepPurple,
                  child: IconButton(
                    icon: const Icon(Icons.send, color: Colors.white),
                    onPressed: () => _sendMessage(_controller.text),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
