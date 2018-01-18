// Copyright 2018 The Bazel Authors. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package com.google.devtools.build.lib.remote.blobstore.http;

import static com.google.common.truth.Truth.assertThat;
import static org.mockito.Mockito.verify;

import com.google.common.net.HttpHeaders;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.ChannelPromise;
import io.netty.channel.embedded.EmbeddedChannel;
import io.netty.handler.codec.http.DefaultHttpResponse;
import io.netty.handler.codec.http.DefaultLastHttpContent;
import io.netty.handler.codec.http.HttpHeaderNames;
import io.netty.handler.codec.http.HttpHeaderValues;
import io.netty.handler.codec.http.HttpMethod;
import io.netty.handler.codec.http.HttpRequest;
import io.netty.handler.codec.http.HttpResponse;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpVersion;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.JUnit4;
import org.mockito.Mockito;

@RunWith(JUnit4.class)
public class HttpDownloadHandlerTest {

  private static final URI CACHE_URI = URI.create("http://storage.googleapis.com:80/cache-bucket");

  @Test
  public void downloadShouldWork() throws IOException {

    // Test that downloading blobs works from both the Action Cache and the CAS. Also test
    // that the handler is reusable.

    EmbeddedChannel ch = new EmbeddedChannel(new HttpDownloadHandler(null));
    downloadShouldWork(true, ch);
    downloadShouldWork(false, ch);
  }

  private void downloadShouldWork(boolean casDownload, EmbeddedChannel ch) throws IOException {
    ByteArrayOutputStream out = Mockito.spy(new ByteArrayOutputStream());
    DownloadCommand cmd = new DownloadCommand(CACHE_URI, casDownload, "abcdef", out);
    ChannelPromise writePromise = ch.newPromise();
    ch.writeOneOutbound(cmd, writePromise);

    HttpRequest request = ch.readOutbound();
    assertThat(request.method()).isEqualTo(HttpMethod.GET);
    assertThat(request.headers().get(HttpHeaderNames.HOST))
        .isEqualTo(CACHE_URI.getHost() + ":" + CACHE_URI.getPort());
    if (casDownload) {
      assertThat(request.uri()).isEqualTo("/cache-bucket/cas/abcdef");
    } else {
      assertThat(request.uri()).isEqualTo("/cache-bucket/ac/abcdef");
    }

    assertThat(writePromise.isDone()).isFalse();

    HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.OK);
    response.headers().set(HttpHeaders.CONTENT_LENGTH, 5);
    response.headers().set(HttpHeaders.CONNECTION, HttpHeaderValues.KEEP_ALIVE);
    ch.writeInbound(response);
    ByteBuf content = Unpooled.buffer();
    content.writeBytes(new byte[] {1, 2, 3, 4, 5});
    ch.writeInbound(new DefaultLastHttpContent(content));

    assertThat(writePromise.isDone()).isTrue();
    assertThat(out.toByteArray()).isEqualTo(new byte[] {1, 2, 3, 4, 5});
    verify(out).close();
    assertThat(ch.isActive()).isTrue();
  }

  @Test
  public void httpErrorsAreSupported() throws IOException {

    // Test that the handler correctly supports http error codes i.e. 404 (NOT FOUND).

    EmbeddedChannel ch = new EmbeddedChannel(new HttpDownloadHandler(null));
    ByteArrayOutputStream out = Mockito.spy(new ByteArrayOutputStream());
    DownloadCommand cmd = new DownloadCommand(CACHE_URI, true, "abcdef", out);
    ChannelPromise writePromise = ch.newPromise();
    ch.writeOneOutbound(cmd, writePromise);

    HttpResponse response =
        new DefaultHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.NOT_FOUND);
    response.headers().set(HttpHeaders.CONNECTION, HttpHeaderValues.CLOSE);
    ch.writeInbound(response);
    assertThat(writePromise.isDone()).isTrue();
    assertThat(writePromise.cause()).isInstanceOf(HttpException.class);
    assertThat(((HttpException) writePromise.cause()).status())
        .isEqualTo(HttpResponseStatus.NOT_FOUND);
    // No data should have been written to the OutputStream and it should have been closed.
    assertThat(out.size()).isEqualTo(0);
    verify(out).close();
    assertThat(ch.isOpen()).isFalse();
  }
}
